# src/storage/sqlite_repo.py
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import List, Dict
from src.shared.schema import Question
from src.storage.interfaces import RunRepositoryP1, RunRepositoryP2, RouteRecord

class SQLiteRunRepository(RunRepositoryP1, RunRepositoryP2):
    def __init__(self, db_path: str = "data/solver.db") -> None:
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        return con

    def init(self) -> None:
        with self._conn() as con:
            cur = con.cursor()
            # P1
            cur.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                  run_id TEXT PRIMARY KEY,
                  paper_path TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                  run_id TEXT NOT NULL,
                  qid TEXT NOT NULL,
                  raw TEXT NOT NULL,
                  stem TEXT NOT NULL,
                  latex TEXT NOT NULL,
                  has_options INTEGER NOT NULL,
                  PRIMARY KEY (run_id, qid),
                  FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS options (
                  run_id TEXT NOT NULL,
                  qid TEXT NOT NULL,
                  idx INTEGER NOT NULL,   -- 0..3
                  text TEXT NOT NULL,
                  PRIMARY KEY (run_id, qid, idx),
                  FOREIGN KEY (run_id, qid) REFERENCES questions(run_id, qid) ON DELETE CASCADE
                );
            """)
            # P2
            cur.execute("""
                CREATE TABLE IF NOT EXISTS routes (
                  run_id     TEXT NOT NULL,
                  qid        TEXT NOT NULL,
                  topic      TEXT NOT NULL,
                  subtopic   TEXT,
                  difficulty TEXT NOT NULL,
                  needs_tools TEXT NOT NULL,     -- JSON array
                  confidence REAL NOT NULL,
                  notes      TEXT,
                  bucket     TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (run_id, qid),
                  FOREIGN KEY (run_id, qid) REFERENCES questions(run_id, qid) ON DELETE CASCADE
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_run ON routes(run_id);")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS route_bucket_counts(
                  run_id TEXT NOT NULL,
                  bucket TEXT NOT NULL,
                  count  INTEGER NOT NULL,
                  PRIMARY KEY(run_id, bucket),
                  FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
            """)
            con.commit()

    # ----- P1 -----
    def upsert_run(self, run_id: str, paper_path: str) -> None:
        with self._conn() as con:
            con.execute(
                "INSERT INTO runs(run_id, paper_path) VALUES(?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET paper_path=excluded.paper_path",
                (run_id, paper_path),
            )
            con.commit()

    def save_questions(self, run_id: str, questions: List[Question]) -> None:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM options WHERE run_id=?", (run_id,))
            cur.execute("DELETE FROM questions WHERE run_id=?", (run_id,))
            q_rows = [(run_id, q["qid"], q["raw"], q["stem"], q.get("latex",""), int(q["has_options"])) for q in questions]
            cur.executemany(
                "INSERT INTO questions(run_id,qid,raw,stem,latex,has_options) VALUES (?,?,?,?,?,?)",
                q_rows,
            )
            opt_rows = []
            for q in questions:
                for i, opt in enumerate(q.get("opts", [])[:4]):
                    opt_rows.append((run_id, q["qid"], i, opt))
            if opt_rows:
                cur.executemany("INSERT INTO options(run_id,qid,idx,text) VALUES (?,?,?,?)", opt_rows)
            con.commit()

    def load_questions(self, run_id: str) -> List[Question]:
        with self._conn() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM questions WHERE run_id=? ORDER BY qid", (run_id,))
            qrows = cur.fetchall()
            cur.execute("SELECT * FROM options WHERE run_id=? ORDER BY qid, idx", (run_id,))
            orows = cur.fetchall()
        opts_map: Dict[str, List[str]] = {}
        for r in orows:
            opts_map.setdefault(r["qid"], []).append(r["text"])
        out: List[Question] = []
        for r in qrows:
            out.append({
                "qid": r["qid"],
                "raw": r["raw"],
                "stem": r["stem"],
                "latex": r["latex"],
                "opts": opts_map.get(r["qid"], []),
                "has_options": bool(r["has_options"]),
            })
        return out

    # ----- P2 -----
    def save_routes(self, run_id: str, routes: List[RouteRecord]) -> None:
        if not routes:
            return
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM routes WHERE run_id=?", (run_id,))
            rows = []
            for r in routes:
                rows.append((
                    run_id,
                    r["qid"],
                    r["topic"],
                    r.get("subtopic"),
                    r["difficulty"],
                    json.dumps(r.get("needs_tools", []), ensure_ascii=False),
                    float(r.get("confidence", 0.0)),
                    r.get("notes"),
                    r["bucket"],
                ))
            cur.executemany("""
                INSERT INTO routes(run_id,qid,topic,subtopic,difficulty,needs_tools,confidence,notes,bucket)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, rows)
            con.commit()

    def load_routes(self, run_id: str) -> List[RouteRecord]:
        with self._conn() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT * FROM routes WHERE run_id=? ORDER BY qid", (run_id,)
            ).fetchall()
        out: List[RouteRecord] = []
        for r in rows:
            out.append({
                "run_id": r["run_id"],
                "qid": r["qid"],
                "topic": r["topic"],
                "subtopic": r["subtopic"],
                "difficulty": r["difficulty"],
                "needs_tools": json.loads(r["needs_tools"] or "[]"),
                "confidence": float(r["confidence"] or 0.0),
                "notes": r["notes"],
                "bucket": r["bucket"],
            })
        return out

    def upsert_bucket_counts(self, run_id: str, counts: Dict[str, int]) -> None:
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM route_bucket_counts WHERE run_id=?", (run_id,))
            rows = [(run_id, b, int(c)) for b, c in counts.items()]
            if rows:
                cur.executemany(
                    "INSERT INTO route_bucket_counts(run_id, bucket, count) VALUES (?,?,?)",
                    rows
                )
            con.commit()

    def load_bucket_counts(self, run_id: str) -> Dict[str, int]:
        with self._conn() as con:
            cur = con.cursor()
            rows = cur.execute(
                "SELECT bucket, count FROM route_bucket_counts WHERE run_id=?",
                (run_id,)
            ).fetchall()
        return {b: int(c) for (b, c) in rows}