"""Clone and select local development databases without carrying Redis state across them."""

import argparse
import os
import re
import signal
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from database_processes import CONNECTION_ENVIRONMENT_KEYS, TmuxProcesses
from dotenv import dotenv_values, set_key, unset_key
from psycopg import sql
from redis import Redis
from redis.exceptions import RedisError
from redis.maint_notifications import MaintNotificationsConfig


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DATABASE_NAME = re.compile(r"[a-z][a-z0-9_]{0,62}")
# One operation per PostgreSQL instance, including helpers in other checkouts.
DATABASE_OPERATION_LOCK = 1186


def settings(path: Path) -> dict[str, str]:
    return {key.upper(): value for key, value in dotenv_values(path).items() if value is not None}


def database_name(value: str) -> str:
    if not DATABASE_NAME.fullmatch(value) or value == "postgres" or value.startswith("template"):
        raise ValueError(
            "Use a database name of 1–63 lowercase letters, digits or underscores, starting with a letter; system names are reserved."
        )
    return value


class DevelopmentConfig:
    def __init__(self, root: Path):
        if any(key.upper() in CONNECTION_ENVIRONMENT_KEYS for key in os.environ):
            raise ValueError(
                "Move database, Redis, Core URL and Flask bind overrides into component .env files and unset them in this shell."
            )
        self.root = root
        self.env_path = root / "src/core/.env"
        if not self.env_path.is_file() or self.env_path.is_symlink():
            raise ValueError("Core needs a regular src/core/.env file. Set up the development environment first.")
        self.core = settings(self.env_path)
        self.frontend = settings(root / "src/frontend/.env")
        self.worker = settings(root / "src/worker/.env")
        if self.core.get("SQLALCHEMY_DATABASE_URI") or self.core.get("SQLALCHEMY_SCHEMA", "postgresql+psycopg") != "postgresql+psycopg":
            raise ValueError(
                "Use Core's DB_URL, DB_USER, DB_PASSWORD and DB_DATABASE settings; remove the explicit database URI/schema override."
            )
        self.selected = database_name(self.core.get("DB_DATABASE", "taranis"))
        endpoint = urlsplit("postgresql://" + self.core.get("DB_URL", "localhost"))
        if endpoint.hostname not in LOCAL_HOSTS or endpoint.username or endpoint.path or endpoint.query or endpoint.fragment:
            raise ValueError(
                "DB_URL must name a loopback PostgreSQL host, optionally with a port. Remote or multi-host databases are not supported."
            )
        self.connection = {
            "host": endpoint.hostname,
            "port": endpoint.port or 5432,
            "user": self.core.get("DB_USER", "taranis"),
            "password": self.core.get("DB_PASSWORD", "supersecret"),
            "connect_timeout": 5,
            "application_name": "taranis-dev-databases",
        }

    def redis_clients(self, stack: ExitStack) -> list[Redis]:
        connections = set()
        for component in (self.core, self.frontend, self.worker):
            broker_url = component.get("REDIS_URL", "redis://localhost:6379/0")
            broker_password = component.get("REDIS_PASSWORD") or None
            connections.add((broker_url, broker_password))
            cache_url = component.get("CACHE_REDIS_URL") or broker_url
            cache_password = component.get("CACHE_REDIS_PASSWORD") or broker_password
            connections.add((cache_url, cache_password))
        clients = []
        for url, password in connections:
            endpoint = urlsplit(url)
            if endpoint.scheme not in {"redis", "rediss"} or endpoint.hostname not in LOCAL_HOSTS:
                raise ValueError("Redis and cache URLs must use dedicated loopback development Redis databases.")
            client = stack.enter_context(
                Redis.from_url(
                    url,
                    password=password,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    maint_notifications_config=MaintNotificationsConfig(enabled=False),
                )
            )
            client.ping()
            clients.append(client)
        return clients

    def processes(self, session: str) -> TmuxProcesses:
        core_port = int(self.core.get("FLASK_RUN_PORT", "5001"))
        frontend_port = int(self.frontend.get("FLASK_RUN_PORT", "5002"))
        core_path = self.core.get("APPLICATION_ROOT", "/").strip("/")
        frontend_path = self.frontend.get("APPLICATION_ROOT", "/frontend").strip("/")
        core_health = f"/{core_path}/api/health" if core_path else "/api/health"
        frontend_health = f"/{frontend_path}/health" if frontend_path else "/health"
        return TmuxProcesses(
            self.root,
            session=session,
            core_url=f"http://127.0.0.1:{core_port}{core_health}",
            frontend_url=f"http://127.0.0.1:{frontend_port}{frontend_health}",
        )


class DatabaseSelection:
    """Prepare the replacement before stopping services; keep exact bytes for rollback."""

    def __init__(self, path: Path, database: str):
        self.path = path
        self.original = path.read_bytes()
        self.mode = path.stat().st_mode & 0o777
        self.prepared = self.stage(self.original)
        try:
            # Remove case variants too: Pydantic's environment keys are case insensitive.
            for key in dotenv_values(self.prepared):
                if key.upper() == "DB_DATABASE":
                    unset_key(self.prepared, key)
            set_key(self.prepared, "DB_DATABASE", database, quote_mode="never")
            self.prepared.chmod(self.mode)
            self.replacement = self.prepared.read_bytes()
        except BaseException:
            self.prepared.unlink(missing_ok=True)
            raise

    def stage(self, content: bytes) -> Path:
        with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=".database-selection-", delete=False) as staged:
            path = Path(staged.name)
            try:
                os.fchmod(staged.fileno(), self.mode)
                staged.write(content)
                staged.flush()
                os.fsync(staged.fileno())
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        return path

    def apply(self):
        if self.path.read_bytes() != self.original:
            raise RuntimeError("Core .env changed during the operation; selection was not changed.")
        self.prepared.replace(self.path)

    def restore(self):
        if self.path.read_bytes() != self.replacement:
            raise RuntimeError("Core .env was edited concurrently; restore DB_DATABASE manually before restarting.")
        previous = self.stage(self.original)
        try:
            previous.replace(self.path)
        finally:
            previous.unlink(missing_ok=True)

    def close(self):
        self.prepared.unlink(missing_ok=True)


def require_database(connection, name: str):
    row = connection.execute("SELECT datallowconn FROM pg_database WHERE datname = %s AND NOT datistemplate", (name,)).fetchone()
    if not row or not row[0]:
        raise ValueError(f"Database {name!r} does not exist or does not accept connections.")


def require_idle_databases(connection, names: list[str]):
    if connection.execute("SELECT 1 FROM pg_stat_activity WHERE datname = ANY(%s) LIMIT 1", (names,)).fetchone():
        raise RuntimeError(
            "Database clients are still connected. Stop remaining services and close SQL clients, then retry; no clients were disconnected."
        )


def clear_redis(clients: list[Redis]):
    for client in clients:
        client.flushdb()


def copy_database(connection, source: str, destination: str):
    require_database(connection, source)
    require_idle_databases(connection, [source])
    # PostgreSQL rejects an existing destination, including a concurrent create.
    connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(destination), sql.Identifier(source)))


def clone_database(connection, config: DevelopmentConfig, name: str, processes: TmuxProcesses | None):
    if connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
        raise ValueError(f"Database {name!r} already exists. Existing databases are never overwritten.")
    if processes:
        processes.stop()
    copy_database(connection, config.selected, name)
    print(f"Cloned {config.selected} to {name}; selected database is still {config.selected}.")
    print("Services remain stopped so restarting cannot migrate the source. Run switch with the database you want to use next.")


def switch_database(connection, config: DevelopmentConfig, name: str, processes: TmuxProcesses | None):
    require_database(connection, name)
    # Check target credentials before touching the running application or selection.
    with psycopg.connect(**config.connection, dbname=name):
        pass
    selection = DatabaseSelection(config.env_path, name)
    try:
        with ExitStack() as stack:
            clients = config.redis_clients(stack)
            if processes:
                processes.stop()
            require_idle_databases(connection, [config.selected, name])
            clear_redis(clients)
            selection.apply()
            try:
                if processes:
                    processes.start(name)
            except BaseException:
                # Never restart the previous database here: this checkout may migrate it.
                try:
                    if processes:
                        processes.stop()
                finally:
                    selection.restore()
                clear_redis(clients)
                raise
    finally:
        selection.close()
    print(f"Selected database: {name}. Disposable Redis queues and caches cleared.")
    if not processes:
        print("Start Core, frontend and workers using your usual development workflow.")


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="development checkout (default: this checkout)")
    cli.add_argument("--session", default="taranis", help="existing development tmux session (default: taranis)")
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="show available databases, sizes, and the saved selection")
    for operation in ("clone", "switch"):
        command = commands.add_parser(operation)
        command.add_argument("name", type=database_name)
        command.add_argument("--stopped", action="store_true", help="all app processes are already stopped; do not manage tmux or restart")
    return cli


def run(args):
    config = DevelopmentConfig(args.root.resolve())
    with psycopg.connect(**config.connection, dbname="postgres", autocommit=True) as connection:
        if args.command == "list":
            print(f"Selected database: {config.selected}")
            for name, size in connection.execute(
                "SELECT datname, pg_size_pretty(pg_database_size(oid)) FROM pg_database "
                "WHERE NOT datistemplate AND datname <> 'postgres' ORDER BY datname"
            ):
                print(f"{'*' if name == config.selected else ' '} {name}\t{size}")
            return
        if not connection.execute("SELECT pg_try_advisory_lock(%s)", (DATABASE_OPERATION_LOCK,)).fetchone()[0]:
            raise RuntimeError("Another database operation is in progress. Retry when it finishes.")
        require_database(connection, config.selected)
        processes = None if args.stopped else config.processes(args.session)
        if processes:
            processes.preflight()
        if args.command == "clone":
            clone_database(connection, config, args.name, processes)
        else:
            switch_database(connection, config, args.name, processes)


def interrupted(_signum, _frame):
    raise KeyboardInterrupt


def main() -> int:
    signal.signal(signal.SIGTERM, interrupted)
    try:
        run(parser().parse_args())
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except psycopg.Error:
        print(
            "Error: PostgreSQL operation failed. Check connectivity, database ownership/CREATEDB privileges, free disk space and active clients.",
            file=sys.stderr,
        )
        return 1
    except RedisError:
        print("Error: Could not clear development Redis. Check its connection and permissions before restarting services.", file=sys.stderr)
        return 1
    except OSError:
        print(
            "Error: Could not update the local environment or run a required program. Check permissions and installed tools.", file=sys.stderr
        )
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Check the selected database with list before restarting services.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
