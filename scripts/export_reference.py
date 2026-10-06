"""Export code-owned reference docs without connecting to services or calling models.

Run from backend with PYTHONPATH=.: python ../scripts/export_reference.py [--check].
"""

import argparse
import json
from pathlib import Path

from app.db import Base
from app.main import app
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def references():
    schema = app.openapi()
    outputs = {"docs/api/openapi.json": json.dumps(schema, indent=2, sort_keys=True) + "\n"}
    endpoint_lines = [
        "# Generated endpoint reference", "",
        "Generated from FastAPI routes. Run `make docs` to refresh or `make docs-check` to detect drift.",
        "This lists declared request contracts; see [API guide](../api.md) for wire behavior and response limits.",
        "Private agent gateway routes are intentionally excluded from OpenAPI.", "",
        "| Method | Path | Parameters | Body | Declared responses |",
        "|---|---|---|---|---|",
    ]
    for path, item in sorted(schema["paths"].items()):
        for method, operation in sorted(item.items()):
            if method not in HTTP_METHODS:
                continue
            parameters = ", ".join(
                f"`{p['name']}` ({p['in']}{', required' if p.get('required') else ''})"
                for p in operation.get("parameters", [])
            ) or "—"
            content = operation.get("requestBody", {}).get("content", {})
            bodies = []
            for mime, body in content.items():
                ref = body.get("schema", {}).get("$ref")
                bodies.append(f"`{mime}`" + (f" → `{ref.rsplit('/', 1)[-1]}`" if ref else ""))
            endpoint_lines.append(
                f"| {method.upper()} | `{path}` | {parameters} | {'; '.join(bodies) or '—'} | "
                f"{', '.join(operation['responses'])} |"
            )
    outputs["docs/api/endpoints.md"] = "\n".join(endpoint_lines) + "\n"
    table_lines = [
        "# Generated PostgreSQL data dictionary", "",
        "Generated from SQLAlchemy metadata with the PostgreSQL dialect. Run `make docs` to refresh.",
        "See [data model](../data-model.md) for logical relationships, migration-only indexes, and lifecycle rules.",
        "Defaults below are application or declared server defaults, not a dump of the live database.", "",
    ]
    dialect = postgresql.dialect()
    for name, table in sorted(Base.metadata.tables.items()):
        table_lines.extend([
            f"## {name}", "", "| Column | PostgreSQL type | Nullable | Key/reference | Default |",
            "|---|---|---|---|---|",
        ])
        for column in table.columns:
            key = "PK" if column.primary_key else ""
            links = ", ".join(fk.target_fullname for fk in column.foreign_keys)
            if links:
                key = "; ".join(filter(None, [key, "FK → " + links]))
            default = column.default or column.server_default
            if default is None:
                default_text = "—"
            elif callable(default.arg):
                default_text = "application callable: " + getattr(default.arg, "__name__", "callable")
            else:
                default_text = str(default.arg).replace("|", "\\|").replace("\n", " ")
            table_lines.append(
                f"| `{column.name}` | `{column.type.compile(dialect=dialect)}` | "
                f"{'yes' if column.nullable else 'no'} | {key or '—'} | {default_text} |"
            )
        unique = sorted(
            ", ".join(c.name for c in constraint.columns)
            for constraint in table.constraints if isinstance(constraint, UniqueConstraint)
        )
        if unique:
            table_lines.extend(["", "Unique constraints: " + "; ".join(f"`{u}`" for u in unique) + "."])
        table_lines.append("")
    outputs["docs/reference/database.md"] = "\n".join(table_lines)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if checked-in references differ from code")
    args = parser.parse_args()
    stale = []
    for relative, content in references().items():
        path = ROOT / relative
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print("Wrote", relative)
    if stale:
        parser.exit(1, "Reference drift: " + ", ".join(stale) + "; run make docs\n")
    if args.check:
        print("OpenAPI, endpoint inventory, and database dictionary match current code")


if __name__ == "__main__":
    main()
