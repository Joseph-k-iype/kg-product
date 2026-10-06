"""Bounded read-only PostgreSQL/HTTP snapshots; no secrets in source metadata."""

import csv
import os
import re
from http.client import HTTPException
from io import StringIO
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from psycopg.rows import dict_row

from app.adapters.structured import csv_data, from_rows, json_rows


def env(name):
    return os.environ.get(name, dotenv_values("../.env").get(name, "")) or ""


def config_check(type, config, location=""):
    allowed = {
        "postgres": {"credential_env", "schema", "table", "limit"},
        "api": {"token_env", "records_path", "format", "limit"},
    }.get(type, set())
    if set(config) - allowed:
        raise ValueError(
            "Source settings contain unsupported fields. Use a credential reference rather than a password or token."
        )
    for name in ("credential_env", "token_env"):
        if config.get(name) and (
            not isinstance(config[name], str) or not re.fullmatch(r"SOURCE_[A-Z0-9_]+", config[name])
        ):
            raise ValueError("Credential references must be server variables starting with SOURCE_.")
    if type == "postgres":
        if not config.get("credential_env") or not config.get("table"):
            raise ValueError("Enter the database credential reference and table name.")
        if any(
            not isinstance(config.get(field, "public"), str) or len(config.get(field, "public")) > 128
            for field in ("table", "schema")
        ):
            raise ValueError("Use schema and table names of at most 128 characters.")
    if type == "api":
        url = urlsplit(location)
        if (
            url.scheme not in ("https", "http")
            or not url.hostname
            or url.username
            or url.password
            or url.fragment
        ):
            raise ValueError("Use an HTTP(S) endpoint without embedded credentials or a fragment.")
        if config.get("format", "json") not in ("json", "csv"):
            raise ValueError("Choose JSON records or CSV for the API response.")
        if not isinstance(config.get("records_path", ""), str):
            raise ValueError("Use a dot-separated JSON records path.")
    if type in ("postgres", "api"):
        limit = config.get("limit", 1000)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10000:
            raise ValueError("Read between 1 and 10,000 records per snapshot.")


class SourceRedirectError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceRedirectError("This endpoint redirects. Register the final, approved endpoint instead.")


def read_source(source):
    config = source.config
    config_check(source.type, config, source.location)
    limit = config.get("limit", 1000)
    if source.type == "postgres":
        reference = config["credential_env"]
        dsn = env(reference)
        if not dsn:
            raise ValueError(
                f"Ask your administrator to configure {reference} on the server, then test again."
            )
        if not dsn.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            raise ValueError("This database connector supports PostgreSQL connection URLs.")
        try:
            with (
                psycopg.connect(
                    dsn.replace("postgresql+psycopg://", "postgresql://"),
                    connect_timeout=5,
                    options="-c default_transaction_read_only=on -c statement_timeout=5000",
                    row_factory=dict_row,
                ) as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(
                    sql.SQL("SELECT * FROM {}.{} LIMIT %s").format(
                        sql.Identifier(config.get("schema", "public")), sql.Identifier(config["table"])
                    ),
                    [limit + 1],
                )
                columns = [column.name for column in cursor.description]
                raw_rows = cursor.fetchall()
        except psycopg.Error:
            raise ValueError(
                "Could not read the database table. Check the credential reference, table name, and read permissions."
            )
        if not raw_rows:
            raise ValueError("The selected table contains no records.")
        rows = [{c: "" if row[c] is None else str(row[c]) for c in columns} for row in raw_rows[:limit]]
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        data = stream.getvalue().encode()
        extension, media_type, normalized = ".csv", "text/csv", from_rows(columns, rows)
        truncated = len(raw_rows) > limit
    elif source.type == "api":
        parsed = urlsplit(source.location)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        approved = {
            value.strip().rstrip("/")
            for value in env("SOURCE_API_ALLOWED_ORIGINS").split(",")
            if value.strip()
        }
        if origin not in approved:
            raise ValueError(
                f"Ask your administrator to approve {origin} in SOURCE_API_ALLOWED_ORIGINS before connecting."
            )
        if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Use HTTPS for external APIs. HTTP is supported only for local development.")
        headers = {"Accept": "application/json, text/csv"}
        reference = config.get("token_env")
        if reference:
            token = env(reference)
            if not token:
                raise ValueError(f"Ask your administrator to configure {reference} on the server.")
            headers["Authorization"] = "Bearer " + token
        try:
            opener = build_opener(ProxyHandler({}), NoRedirect())
            with opener.open(Request(source.location, headers=headers, method="GET"), timeout=8) as response:
                data = response.read(5 * 1024 * 1024 + 1)
        except SourceRedirectError:
            raise ValueError("This endpoint redirects. Register the final, approved endpoint instead.")
        except (URLError, HTTPException, OSError, ValueError):
            raise ValueError("Could not read this API. Check its endpoint, credentials, and availability.")
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("The API response exceeds 5 MB. Use a smaller or paginated endpoint.")
        if config.get("format", "json") == "csv":
            columns, all_rows = csv_data(data)
            extension, media_type, kind = ".csv", "text/csv", "csv"
        else:
            columns, all_rows = json_rows(data, config.get("records_path", ""))
            extension, media_type, kind = ".json", "application/json", "json"
        normalized = from_rows(columns, all_rows[:limit], kind)
        normalized["records_path"] = config.get("records_path", "")
        truncated = len(all_rows) > limit
    else:
        raise ValueError(
            "This source is a registered location. Use file imports, or configure a PostgreSQL/HTTP API connection."
        )
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("This snapshot exceeds 20 MB. Read fewer records.")
    return {
        "data": data,
        "extension": extension,
        "media_type": media_type,
        "normalized": normalized,
        "preview": {
            "record_count": len(normalized["records"]),
            "columns": normalized["columns"],
            "sample_rows": normalized["sample_rows"],
            "truncated": truncated,
            "message": f"Showing the first {limit} records; more data is available."
            if truncated
            else "Connection works. These records can be imported into a draft.",
        },
    }
