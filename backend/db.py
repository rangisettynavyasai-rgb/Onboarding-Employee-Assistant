#!/usr/bin/env python3
"""
Company AI Assistant: Master Database Layer
Directly initialized from and synchronized with bigquery/tables.sql and bigquery/seed_data.sql.
Provides relational persistence for employees, onboarding tasks, knowledge assets,
knowledge chunks, timesheets, incidents, team escalation mesh, and telemetry friction logs.
Ensures zero hardcoded in-memory state; all operations read and write directly to the database.
"""

import os
import sys
import sqlite3
import re
from typing import Dict, List, Any, Optional

DB_FILE_PATH = os.path.join(os.path.dirname(__file__), "enterprise.db")
TABLES_SQL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bigquery", "tables.sql")
SEED_SQL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bigquery", "seed_data.sql")


def strip_bq_options(line: str) -> str:
    """Removes BigQuery OPTIONS(...) clauses including nested parentheses while preserving commas."""
    m = re.search(r"OPTIONS\s*\(", line, re.I)
    while m:
        start_idx = m.start()
        inner_idx = m.end() - 1
        depth = 0
        end_idx = -1
        for i in range(inner_idx, len(line)):
            if line[i] == "(":
                depth += 1
            elif line[i] == ")":
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        if end_idx != -1:
            line = line[:start_idx] + line[end_idx:]
            m = re.search(r"OPTIONS\s*\(", line, re.I)
        else:
            break
    return line


def transform_schema_to_sql(schema_sql: str) -> str:
    """Transforms BigQuery DDL (tables.sql) to standard relational SQL."""
    # Remove CREATE SCHEMA block
    schema_sql = re.sub(r"CREATE\s+SCHEMA[\s\S]*?\);", "", schema_sql, flags=re.IGNORECASE)
    lines = []
    for line in schema_sql.splitlines():
        line = strip_bq_options(line)
        # Remove dataset / project prefix
        line = re.sub(r"`[^`]*\.employee_ai\.([^`]+)`", r"\1", line)
        line = re.sub(r"CREATE\s+OR\s+REPLACE\s+TABLE", "CREATE TABLE IF NOT EXISTS", line, flags=re.IGNORECASE)
        line = re.sub(r"\bSTRING\b", "TEXT", line)
        line = re.sub(r"\bBOOLEAN\b", "INTEGER", line)
        line = re.sub(r"\bINT64\b", "INTEGER", line)
        line = re.sub(r"\bFLOAT64\b", "REAL", line)
        line = re.sub(r"\bDATE\b", "TEXT", line)
        line = re.sub(r"\bTIMESTAMP\b", "TEXT", line)
        lines.append(line)
    return "\n".join(lines)


def transform_seed_to_sql(seed_sql: str) -> str:
    """Transforms BigQuery DML seed data (seed_data.sql) to standard relational SQL."""
    lines = []
    for line in seed_sql.splitlines():
        line = re.sub(r"`[^`]*\.employee_ai\.([^`]+)`", r"\1", line)
        line = re.sub(r"\bTRUE\b", "1", line)
        line = re.sub(r"\bFALSE\b", "0", line)
        line = re.sub(r"\bCURRENT_TIMESTAMP\(\)", "CURRENT_TIMESTAMP", line, flags=re.IGNORECASE)
        lines.append(line)
    return "\n".join(lines)


class Database:
    """Primary SQL Database Engine sourced directly from BigQuery schemas and synthetic seeds."""

    _instance: Optional["Database"] = None

    def __init__(self, db_path: str = DB_FILE_PATH):
        self.db_path = db_path
        self._ensure_initialized()

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_initialized(self):
        """Initializes tables and seeds from bigquery/ folder if not present."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                print(f"[Database] Bootstrapping database from {TABLES_SQL_PATH} and {SEED_SQL_PATH}...", file=sys.stderr)
                if os.path.exists(TABLES_SQL_PATH):
                    with open(TABLES_SQL_PATH, "r", encoding="utf-8") as f:
                        tables_content = f.read()
                    schema_sql = transform_schema_to_sql(tables_content)
                    for stmt in schema_sql.split(";"):
                        clean_stmt = stmt.strip()
                        if clean_stmt:
                            conn.execute(clean_stmt)
                    conn.commit()

                if os.path.exists(SEED_SQL_PATH):
                    with open(SEED_SQL_PATH, "r", encoding="utf-8") as f:
                        seed_content = f.read()
                    seed_sql = transform_seed_to_sql(seed_content)
                    for stmt in seed_sql.split(";"):
                        clean_stmt = stmt.strip()
                        if clean_stmt:
                            conn.execute(clean_stmt)
                    conn.commit()
                print("[Database] Schema and synthetic seed data initialized successfully.", file=sys.stderr)

            # Ensure chat_sessions table exists for persistent conversation history
            conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                history_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL
            );
            """)
            conn.commit()
        except Exception as e:
            print(f"[Database] Initialization error: {e}", file=sys.stderr)
            conn.rollback()
        finally:
            conn.close()

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a SELECT query and returns rows as dictionaries."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Executes a SELECT query and returns the first row as a dictionary or None."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def execute(self, sql: str, params: tuple = ()) -> int:
        """Executes an INSERT, UPDATE, or DELETE statement and returns affected rows count."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()


db = Database.get_instance()
