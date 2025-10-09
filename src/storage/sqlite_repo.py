# src/storage/sqlite_repo.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Dict
from src.shared.schema import Question
from src.storage.interfaces import RunRepositoryP1

class SQLiteRunRepository(RunRepositoryP1):
    def __init__(self, db_path: str = "data/solver.db") -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.execute("PRAGMA foreign_keys=ON;")
        return con

    def init(self) -> None:
        with self._connect() as con:
            cur = con.cursor()
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
            con.commit()

    def upsert_run(self, run_id: str, paper_path: str) -> None:
        with self._connect() as con:
            con.execute(
                "INSERT INTO runs(run_id, paper_path) VALUES(?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET paper_path=excluded.paper_path",
                (run_id, paper_path),
            )
            con.commit()

    def save_questions(self, run_id: str, questions: List[Question]) -> None:
        with self._connect() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM options WHERE run_id=?", (run_id,))
            cur.execute("DELETE FROM questions WHERE run_id=?", (run_id,))
            q_rows = [(run_id, q["qid"], q["raw"], q["stem"], q["latex"], int(q["has_options"]))
                      for q in questions]
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
        with self._connect() as con:
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