#!/usr/bin/env python
'''
# Edge History Export Tool

This Python script will:
1. Copy the Edge History file to the current directory with a timestamped filename.
2. Open the copied SQLite database.
3. Export the contents of the `urls`, `downloads`, and `downloads_url_chains` tables to separate Markdown files.

---
'''

import os
import sys
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Any

def copy_history_file(src_path, dest_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest_filename = f"History_{timestamp}.db"
    dest_path = os.path.join(dest_dir, dest_filename)
    shutil.copy2(src_path, dest_path)
    return dest_path

def export_table_to_md(db_path: str, table: str, md_path: str, columns: Optional[List[str]] = None) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if columns is None:
        cur.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cur.fetchall()]
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()

    # Only special handling for 'urls' table
    if table == 'urls':
        # Edge timestamps are in Webkit format: microseconds since 1601-01-01
        def edge_ts_to_dt(ts: Any) -> Optional[datetime]:
            try:
                return datetime(1601, 1, 1) + timedelta(microseconds=int(ts))
            except Exception:
                return None

        now: datetime = datetime.now()
        day_ago: datetime = now - timedelta(days=1)
        week_ago: datetime = now - timedelta(days=7)
        month_ago: datetime = now - timedelta(days=30)

        with_ts: List[Tuple[datetime, List[Any]]] = []
        without_ts: List[List[Any]] = []
        for row in rows:
            ts = row[columns.index('last_visit_time')]
            dt = edge_ts_to_dt(ts)
            if dt:
                with_ts.append((dt, row))
            else:
                without_ts.append(row)

        with_ts.sort(key=lambda x: x[0], reverse=True)
        without_ts.sort(key=lambda r: r[columns.index('url')])

        groups: dict[str, List[List[Any]]] = {
            'Last Day': [],
            'Last Week': [],
            'Last Month': [],
            'Older': []
        }
        for dt, row in with_ts:
            if dt >= day_ago:
                groups['Last Day'].append((dt, row))
            elif dt >= week_ago:
                groups['Last Week'].append((dt, row))
            elif dt >= month_ago:
                groups['Last Month'].append((dt, row))
            else:
                groups['Older'].append((dt, row))

        # Add ISO timestamp column to output
        out_columns = columns + ['last_visit_iso']

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {table} table\n\n")
            for group, group_rows in groups.items():
                f.write(f"## {group}\n\n")
                f.write("| " + " | ".join(out_columns) + " |\n")
                f.write("|" + "|".join(['---'] * len(out_columns)) + "|\n")
                for dt, row in group_rows:
                    iso = dt.isoformat() if dt else ''
                    f.write("| " + " | ".join(str(item) for item in row) + f" | {iso} |\n")
                f.write("\n")
            f.write("## No Timestamp (Alphabetical)\n\n")
            f.write("| " + " | ".join(out_columns) + " |\n")
            f.write("|" + "|".join(['---'] * len(out_columns)) + "|\n")
            for row in without_ts:
                f.write("| " + " | ".join(str(item) for item in row) + " |  |\n")
    else:
        # Default: just dump all rows
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {table} table\n\n")
            f.write("| " + " | ".join(columns) + " |\n")
            f.write("|" + "|".join(['---'] * len(columns)) + "|\n")
            for row in rows:
                f.write("| " + " | ".join(str(item) for item in row) + " |\n")
    conn.close()

def main():
    import sys
    if len(sys.argv) > 1:
        src_history = sys.argv[1]
    else:
        # src_history = r"C:\\Users\\USERNAME\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History"
        print('Usage: py-export-ms-edge-history.exe <path to MS edge history file>')
        print('Example: py-export-ms-edge-history.exe "C:\\Users\\USERNAME\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History"')
        sys.exit(1)
    
    dest_dir = os.path.dirname(os.path.abspath(__file__))
    print('DEBUG:: dest_dir: ' + dest_dir)
    db_path = copy_history_file(src_history, dest_dir)
    tables = {
        'urls': None,
        'downloads': None,
        'downloads_url_chains': None
    }
    for table in tables:
        md_path = os.path.join(dest_dir, f"{table}.md")
        export_table_to_md(db_path, table, md_path)
    print(f"Export complete. Markdown files created for each table. Source: {src_history}")

if __name__ == "__main__":
    main()
