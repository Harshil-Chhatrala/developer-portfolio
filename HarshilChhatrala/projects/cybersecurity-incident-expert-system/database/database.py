"""SQLite persistence layer for incident diagnostic history logs."""

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List


class DatabaseManager:
  """Manages SQLite storage for past assessment sessions."""

  def __init__(self, db_path: Path = None):
    if db_path is None:
      db_path = Path(__file__).parent / "history.db"
    self.db_path = db_path
    self.init_db()

  def get_connection(self) -> sqlite3.Connection:
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    return conn

  def init_db(self) -> None:
    """Initializes database schema if missing."""
    with self.get_connection() as conn:
      conn.execute("""
                CREATE TABLE IF NOT EXISTS assessment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    observations_json TEXT NOT NULL,
                    primary_diagnosis TEXT,
                    confidence REAL,
                    risk_label TEXT,
                    full_result_json TEXT NOT NULL
                )
            """)
      conn.commit()

  def save_assessment(
      self, observations: List[str], result: Dict[str, Any]
  ) -> int:
    """Saves assessment execution results into SQLite."""
    primary_diag = "Insufficient Evidence"
    confidence = 0.0
    risk_label = "N/A"

    if not result.get("insufficient_evidence") and result.get("diagnoses"):
      top = result["diagnoses"][0]
      primary_diag = top["name"]
      confidence = top["confidence"]
      risk_label = top["risk_label"]

    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO assessment_history 
                (observations_json, primary_diagnosis, confidence, risk_label, full_result_json)
                VALUES (?, ?, ?, ?, ?)
            """,
          (
              json.dumps(observations),
              primary_diag,
              confidence,
              risk_label,
              json.dumps(result),
          ),
      )
      conn.commit()
      return cursor.lastrowid

  def get_all_assessments(self) -> List[Dict[str, Any]]:
    """Retrieves history records."""
    with self.get_connection() as conn:
      cursor = conn.cursor()
      cursor.execute("""
                SELECT id, timestamp, primary_diagnosis, confidence, risk_label, observations_json 
                FROM assessment_history 
                ORDER BY timestamp DESC
            """)
      rows = cursor.fetchall()
      return [dict(row) for row in rows]