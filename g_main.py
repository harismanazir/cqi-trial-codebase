
"""
Safe and efficient user ingestion example.

Features:
- Input validation
- Parameterized SQL (prevents injection)
- Streams files (low memory)
- Compiles regex once
- Uses context managers for resources
- Proper logging and error handling
- Type hints and docstrings
"""

from __future__ import annotations
import sqlite3
import requests
import logging
import re
from pathlib import Path
from typing import Dict, Generator, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER_ROLE_RE = re.compile(r"\badmin\b", flags=re.IGNORECASE)

def stream_lines(path: str) -> Generator[str, None, None]:
    """Yield lines from a file lazily to avoid high memory usage."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{path} not found")
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            yield line.rstrip("\n")

@lru_cache(maxsize=1024)
def heavy_cached(x: int) -> int:
    """Expensive computation cached to avoid repeated work."""
    s = 0
    for i in range(100000):
        s += (i * x) % 97
    return s

def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            );
        """)

def insert_user(conn: sqlite3.Connection, name: str, email: str, role: str = "user") -> None:
    """
    Insert a user into the database using parameterized SQL (prevents injection).
    """
    with conn:
        conn.execute(
            "INSERT INTO users (name, email, role) VALUES (?, ?, ?)",
            (name, email, role),
        )

def parse_line_safe(line: str) -> Dict[str, str] | None:
    """
    Parse an expected key=value CSV-like line, e.g.:
    name=Alice,email=alice@example.com,role=admin

    Returns a dict or None if parsing fails.
    """
    parts = line.split(",")
    out: Dict[str, str] = {}
    try:
        for p in parts:
            if not p:
                continue
            k, v = p.split("=", 1)
            out[k.strip()] = v.strip()
    except ValueError:
        return None
    # Basic validation
    if "name" not in out or "email" not in out:
        return None
    return out

def process_users_stream(file_path: str, conn: sqlite3.Connection, admin_handler=None) -> int:
    """
    Read users line-by-line, validate, and insert into DB.
    Returns number of inserted users.
    """
    inserted = 0
    for line in stream_lines(file_path):
        parsed = parse_line_safe(line)
        if not parsed:
            logger.debug("Skipping malformed line: %s", line)
            continue
        name = parsed["name"]
        email = parsed["email"]
        role = parsed.get("role", "user")
        insert_user(conn, name, email, role)
        inserted += 1
        if USER_ROLE_RE.search(role):
            if admin_handler:
                admin_handler(name, email)
    return inserted

def send_data_secure(url: str, payload: dict, timeout: float = 10.0) -> requests.Response:
    """
    Send JSON data with SSL verification enabled and timeouts.
    Raises for HTTP errors to make failures visible.
    """
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r

def parallel_orchestrate(file_paths: Iterable[str]) -> None:
    """
    Example orchestration using threads while streaming files to avoid memory spikes.
    Demonstrates safe concurrency with ThreadPoolExecutor.
    """
    def task(path: str) -> int:
        # simple task: count non-empty lines
        count = sum(1 for _ in stream_lines(path))
        return count

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(task, p): p for p in file_paths}
        for fut in as_completed(futures):
            path = futures[fut]
            try:
                result = fut.result()
                logger.info("File %s has %d lines", path, result)
            except Exception as exc:
                logger.exception("Error processing %s: %s", path, exc)

def main():
    """Main entry point."""
    db_path = ":memory:"
    with sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        init_db(conn)
        try:
            inserted = process_users_stream("users.txt", conn, admin_handler=lambda n, e: logger.info("Admin user: %s <%s>", n, e))
            logger.info("Inserted %d users", inserted)
        except FileNotFoundError:
            logger.warning("users.txt not found; skipping user import")
        # safe network call example (will raise on HTTP error)
        try:
            resp = send_data_secure("https://example.com/ingest", {"inserted": inserted})
            logger.info("Send result: %s", resp.status_code)
        except Exception as exc:
            logger.exception("Failed to send data: %s", exc)

        # Orchestrate other file processing in parallel
        parallel_orchestrate(["input1.txt", "input2.txt"])

if __name__ == "__main__":
    main()
