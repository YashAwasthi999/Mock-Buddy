import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


PROJECT_DATA_DIR = Path(__file__).resolve().parents[2] / "DATA"
DATA_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "DATA" / "uploads"
DATABASE_PATH = DATA_UPLOAD_DIR / "mock_buddy.sqlite3"


@contextmanager
def _connection(database_path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    if not database_path.parent.is_dir():
        raise FileNotFoundError(
            f"Interview storage folder does not exist: {database_path.parent}"
        )
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_storage(database_path: Path = DATABASE_PATH) -> None:
    """Create the local database tables if they do not already exist."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connection(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS interviews (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL DEFAULT 'local',
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resume_filename TEXT NOT NULL,
                resume_text TEXT NOT NULL,
                round_key TEXT NOT NULL,
                round_name TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed')),
                overall_feedback TEXT,
                suggestions TEXT,
                total_score INTEGER,
                max_score INTEGER,
                raw_feedback TEXT
            );

            CREATE TABLE IF NOT EXISTS interview_answers (
                interview_id TEXT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
                question_index INTEGER NOT NULL CHECK (question_index >= 0),
                question TEXT NOT NULL,
                answer TEXT,
                score INTEGER CHECK (score IS NULL OR (score >= 0 AND score <= 10)),
                PRIMARY KEY (interview_id, question_index)
            );
            """
        )
        interview_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(interviews)")
        }
        if "owner_id" not in interview_columns:
            connection.execute(
                "ALTER TABLE interviews ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'"
            )

    legacy_database_paths = (
        PROJECT_DATA_DIR / database_path.name,
        PROJECT_DATA_DIR / "uploads" / database_path.name,
    )
    for legacy_database_path in legacy_database_paths:
        if legacy_database_path == database_path or not legacy_database_path.is_file():
            continue

        with _connection(database_path) as connection:
            connection.execute("ATTACH DATABASE ? AS legacy", (str(legacy_database_path),))
            connection.execute(
                """
                INSERT OR IGNORE INTO interviews (
                    id, started_at, updated_at, resume_filename, resume_text,
                    round_key, round_name, status, overall_feedback, suggestions,
                    total_score, max_score, raw_feedback
                )
                SELECT id, started_at, updated_at, resume_filename, resume_text,
                       round_key, round_name, status, overall_feedback, suggestions,
                       total_score, max_score, raw_feedback
                FROM legacy.interviews
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO interview_answers (
                    interview_id, question_index, question, answer, score
                )
                SELECT interview_id, question_index, question, answer, score
                FROM legacy.interview_answers
                """
            )

def create_interview(
    resume_filename: str,
    resume_text: str,
    round_key: str,
    round_name: str,
    questions: list[str],
    database_path: Path = DATABASE_PATH,
    owner_id: str = "local",
) -> str:
    """Persist the resume and generated questions before the interview begins."""
    if not questions:
        raise ValueError("An interview must have at least one question.")

    interview_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO interviews (
                id, owner_id, started_at, updated_at, resume_filename, resume_text,
                round_key, round_name, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'in_progress')
            """,
            (
                interview_id,
                owner_id,
                timestamp,
                timestamp,
                resume_filename,
                resume_text,
                round_key,
                round_name,
            ),
        )
        connection.executemany(
            """
            INSERT INTO interview_answers (interview_id, question_index, question)
            VALUES (?, ?, ?)
            """,
            [
                (interview_id, index, question)
                for index, question in enumerate(questions)
            ],
        )
    return interview_id


def save_answer(
    interview_id: str,
    question_index: int,
    answer: str,
    database_path: Path = DATABASE_PATH,
    owner_id: str = "local",
) -> None:
    """Persist an answer as soon as it is submitted."""
    cleaned_answer = answer.strip()
    if not cleaned_answer:
        raise ValueError("An answer cannot be empty.")

    with _connection(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE interview_answers
            SET answer = ?
            WHERE interview_id = ? AND question_index = ?
              AND EXISTS (
                  SELECT 1 FROM interviews
                  WHERE id = ? AND owner_id = ? AND status = 'in_progress'
              )
            """,
            (cleaned_answer, interview_id, question_index, interview_id, owner_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("The interview question was not found or is no longer active.")
        connection.execute(
            "UPDATE interviews SET updated_at = ? WHERE id = ? AND owner_id = ?",
            (datetime.now(timezone.utc).isoformat(), interview_id, owner_id),
        )


def save_feedback(
    interview_id: str,
    feedback: dict,
    database_path: Path = DATABASE_PATH,
    owner_id: str = "local",
) -> None:
    """Persist AI feedback and mark the interview complete after validating answers."""
    scores = feedback.get("scores_per_question")
    if not isinstance(scores, list) or not scores:
        raise ValueError("Feedback must contain a score for every interview answer.")
    if any(type(score) is not int or not 0 <= score <= 10 for score in scores):
        raise ValueError("Feedback scores must be whole numbers from 0 to 10.")

    with _connection(database_path) as connection:
        answer_rows = connection.execute(
            """
            SELECT question_index, answer
            FROM interview_answers AS answers
            WHERE interview_id = ?
              AND EXISTS (
                  SELECT 1 FROM interviews
                  WHERE id = answers.interview_id AND owner_id = ?
              )
            ORDER BY question_index
            """,
            (interview_id, owner_id),
        ).fetchall()
        if len(answer_rows) != len(scores) or any(not row["answer"] for row in answer_rows):
            raise ValueError("Save feedback only after every interview question has an answer and score.")

        updated = connection.execute(
            """
            UPDATE interviews
            SET updated_at = ?, status = 'completed',
                overall_feedback = ?, suggestions = ?, total_score = ?,
                max_score = ?, raw_feedback = ?
            WHERE id = ? AND owner_id = ? AND status = 'in_progress'
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                feedback["overall_feedback"],
                feedback["suggestions"],
                sum(scores),
                len(scores) * 10,
                feedback.get("raw_output"),
                interview_id,
                owner_id,
            ),
        )
        if updated.rowcount != 1:
            raise ValueError("The interview was not found or has already been completed.")
        connection.executemany(
            """
            UPDATE interview_answers
            SET score = ?
            WHERE interview_id = ? AND question_index = ?
            """,
            [
                (score, interview_id, index)
                for index, score in enumerate(scores)
            ],
        )


def list_interviews(
    limit: int = 20,
    database_path: Path = DATABASE_PATH,
    owner_id: str = "local",
) -> list[dict]:
    """Return recent saved interviews for the app's history panel."""
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id, started_at, updated_at, resume_filename, round_name,
                   status, total_score, max_score
            FROM interviews
            WHERE owner_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (owner_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_interview(
    interview_id: str,
    database_path: Path = DATABASE_PATH,
    owner_id: str = "local",
) -> dict | None:
    """Return a saved interview, including the resume, answers, scores, and feedback."""
    with _connection(database_path) as connection:
        interview = connection.execute(
            "SELECT * FROM interviews WHERE id = ? AND owner_id = ?",
            (interview_id, owner_id),
        ).fetchone()
        if interview is None:
            return None

        result = dict(interview)
        result["answers"] = [
            dict(row)
            for row in connection.execute(
                """
                SELECT question_index, question, answer, score
                FROM interview_answers
                WHERE interview_id = ?
                ORDER BY question_index
                """,
                (interview_id,),
            ).fetchall()
        ]
    return result
