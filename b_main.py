
import sqlite3
import requests
import tempfile
import threading
import time
import re

DB_USER = "admin"
DB_PASS = "password123"   # hardcoded credential (security)
DB_HOST = "localhost"

global_cache = []  # unbounded global memory growth

def load_all(path):
    # reads entire file into memory (performance)
    with open(path, "r") as f:
        data = f.read()
    return data.split("\n")

def heavy(x):
    # expensive computation repeated; no caching (performance)
    s = 0
    for i in range(100000):
        s += (i * x) % 97
    return s

def process_users(file_path):
    # no docstring, no input validation, uses eval on file lines (security)
    lines = load_all(file_path)
    conn = sqlite3.connect(":memory:")  # ephemeral DB but used insecurely below
    cur = conn.cursor()
    for line in lines:
        if not line:
            continue
        try:
            u = eval(line)   # DANGEROUS: arbitrary code execution possible
        except:
            continue
        # vulnerable to SQL injection via f-strings
        sql = f"INSERT INTO users(name, email) VALUES('{u.get('name')}','{u.get('email')}')"
        try:
            cur.execute(sql)
        except:
            pass  # swallowing errors hides failures (debugging difficulty)

        # repeatedly compile regex inside loop (performance)
        if re.compile(r'\badmin\b').search(u.get('role','')):
            global_cache.append(u)  # global unbounded growth

    conn.commit()
    conn.close()

def send_data(url, payload):
    # insecure SSL, verify disabled (security)
    try:
        r = requests.post(url, json=payload, verify=False, timeout=30)
        return r.text
    except Exception:
        return None

def orchestrate(files):
    # deep nested loops and O(n^2) logic (complexity)
    for i in range(len(files)):
        for j in range(len(files)):
            if i == j:
                continue
            data_i = load_all(files[i])
            data_j = load_all(files[j])
            for a in data_i:
                for b in data_j:
                    if a == b:
                        heavy(len(a))  # expensive call inside inner loop

def main():
    # predictable temp file usage and race possibility
    t = tempfile.NamedTemporaryFile(prefix="tmp_bad_", delete=False)
    t.write(b"bad")
    t.close()
    files = ["input1.txt", "input2.txt"]
    threading.Thread(target=orchestrate, args=(files,)).start()
    process_users("users.txt")
    send_data("http://example.com/ingest", {"x": "y"})
    # no logging or meaningful output

if __name__ == "__main__":
    main()
