import ast
import re
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
SQL_IDENTIFIER = r'(?:"(?:[^"]|"")+"|[a-z_][a-z_0-9$]*)'
QUALIFIED_SQL_OBJECT = re.compile(
    r"\b(?:TABLE|TYPE|SEQUENCE|INDEX|VIEW|FUNCTION|REFERENCES|INTO|UPDATE|FROM|JOIN|TRUNCATE)\s+"
    r"(?:IF\s+(?:NOT\s+)?EXISTS\s+)?(?:ONLY\s+)?"
    rf"(?P<schema>{SQL_IDENTIFIER})\s*\.\s*{SQL_IDENTIFIER}",
    re.IGNORECASE,
)


def test_migrations_do_not_hardcode_application_schemas():
    migrations = sorted(MIGRATIONS_DIR.glob("*.py"))
    assert migrations, "No migration files found"
    violations = []
    for path in migrations:
        # Inspect strings without importing migrations or executing their callbacks.
        # This covers both forward and rollback SQL, including SQL in Python steps.
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for match in QUALIFIED_SQL_OBJECT.finditer(node.value):
                schema = match["schema"].strip('"').lower()
                # PostgreSQL metadata has a fixed namespace; application data does not.
                if schema not in {"information_schema", "pg_catalog"}:
                    violations.append(f"{path.name}:{node.lineno}: {match[0]}")

    assert not violations, "Use unqualified application objects so migrations respect search_path:\n" + "\n".join(violations)
