"""Scoped SQLAlchemy observations supplement native profiler artifacts."""

import hashlib
import inspect
import re
import time
from collections import Counter
from contextlib import AbstractContextManager

import psycopg
from psycopg.rows import dict_row
from sqlalchemy import event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session


class Observations(AbstractContextManager):
    def __init__(self, *, stacks=False):
        self.stacks = stacks
        self.statements = []
        self.counters = Counter()
        self._listeners = []
        self._started = {}
        self.explain_candidates = {}
        self.engines = set()
        self.relationships = set()

    def __enter__(self):
        for target, name, callback in (
            (Engine, "before_cursor_execute", self.before_execute),
            (Engine, "after_cursor_execute", self.after_execute),
            (Engine, "handle_error", self.failed_execute),
            (Engine, "begin", self.begin),
            (Engine, "commit", self.commit),
            (Engine, "rollback", self.rollback),
            (Session, "before_flush", self.flush),
            (Session, "do_orm_execute", self.orm_execute),
        ):
            event.listen(target, name, callback)
            self._listeners.append((target, name, callback))
        return self

    def __exit__(self, *args):
        for listener in reversed(self._listeners):
            event.remove(*listener)
        self._listeners.clear()
        return False

    def before_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.engines.add(conn.engine)
        self._started[id(context)] = time.perf_counter()

    def after_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.record(cursor, statement, parameters, context, executemany)

    def failed_execute(self, context):
        self.counters["failed_statements"] += 1
        started = self._started.pop(id(context.execution_context), None)
        if started is not None:
            duration = time.perf_counter() - started
            self.counters["statements"] += 1
            self.counters["cursor_seconds"] += duration
            self.statements.append(
                {
                    "fingerprint": hashlib.sha256((context.statement or "").encode()).hexdigest(),
                    "cursor_seconds": duration,
                    "failed": True,
                    "row_count": None,
                }
            )

    def record(self, cursor, statement, parameters, context, executemany):
        duration = time.perf_counter() - self._started.pop(id(context), time.perf_counter())
        fingerprint = hashlib.sha256(statement.encode()).hexdigest()
        entry = {
            "fingerprint": fingerprint,
            "cursor_seconds": duration,
            "row_count": cursor.rowcount if cursor.rowcount >= 0 else None,
            "executemany": executemany,
        }
        if self.stacks:
            # Never persist bound parameters or SQL literals from production snapshots.
            entry["calls"] = application_stack()
        self.statements.append(entry)
        self.counters["statements"] += 1
        self.counters["cursor_seconds"] += duration
        compiled_statement = getattr(getattr(context, "compiled", None), "statement", None)
        if (getattr(compiled_statement, "is_select", False) or statement.lstrip().upper().startswith("SELECT")) and not executemany:
            self.explain_candidates.setdefault(fingerprint, (statement, parameters))

    def commit(self, conn):
        self.counters["commits"] += 1

    def begin(self, conn):
        self.counters["transactions_begun"] += 1

    def rollback(self, conn):
        self.counters["rollbacks"] += 1

    def flush(self, session, context, instances):
        self.counters["flushes"] += 1

    def orm_execute(self, state):
        if state.is_relationship_load:
            self.counters["relationship_loads"] += 1
            for item in state.loader_strategy_path.path:
                if hasattr(item, "key") and hasattr(item, "parent"):
                    parent = item.parent.class_
                    self.relationships.add(f"{parent.__module__}.{parent.__qualname__}.{item.key}")
        if state.is_column_load:
            self.counters["column_refreshes"] += 1

    def as_dict(self):
        return {"counters": dict(self.counters), "statements": self.statements, "relationships": sorted(self.relationships)}


def application_stack():
    calls = []
    frame = inspect.currentframe()
    try:
        while frame:
            module = frame.f_globals.get("__name__", "")
            if module.startswith("core."):
                calls.append(f"{module}.{frame.f_code.co_qualname}")
            frame = frame.f_back
    finally:
        del frame
    return calls


def postgres_connection(uri, *, database=None):
    url = make_url(uri)
    isolated_name = url.database in {"orm_profile", "orm_correctness"} or bool(re.fullmatch(r"orm_case_[0-9a-f]{32}", url.database or ""))
    if url.drivername != "postgresql+psycopg" or not isolated_name:
        raise ValueError("Profiling requires a disposable orm_profile or orm_correctness PostgreSQL database")
    connection = psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname=database or url.database,
        autocommit=True,
        row_factory=dict_row,
    )
    ownership = connection.execute(
        "SELECT shobj_description(oid, 'pg_database') AS marker FROM pg_database WHERE datname = %s", (url.database,)
    ).fetchone()
    if not ownership or ownership["marker"] != "taranis-orm-disposable-v1":
        connection.close()
        raise ValueError("Database is not marked as disposable by the isolated ORM Compose runner")
    return connection


def reset_server_statistics(connection):
    connection.execute("SELECT pg_stat_statements_reset()")


def server_statistics(connection):
    return connection.execute("""
        SELECT queryid::text, query, calls, total_exec_time, rows, shared_blks_hit,
               shared_blks_read, shared_blks_dirtied, shared_blks_written,
               temp_blks_read, temp_blks_written, wal_records, wal_bytes::float8,
               shared_blk_read_time, shared_blk_write_time
        FROM pg_stat_statements
        WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
          AND query NOT LIKE '%pg_stat_statements%'
          AND query NOT LIKE '%shobj_description%'
    """).fetchall()


def capture_plans(uri, candidates):
    plans = {}
    # Parameters live only in memory; EXPLAIN output can contain values and stays local.
    with postgres_connection(uri) as connection:
        for fingerprint, (statement, parameters) in candidates.items():
            try:
                with connection.transaction(force_rollback=True):
                    connection.execute("SET TRANSACTION READ ONLY")
                    result = connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters).fetchone()
                    plans[fingerprint] = next(iter(result.values()))
            except psycopg.Error:
                plans[fingerprint] = {"status": "unavailable"}
    return plans
