import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).resolve().parents[1]
mock_interview_root = project_root / "Mock_INTERVIEW"
if str(mock_interview_root) not in sys.path:
    sys.path.insert(0, str(mock_interview_root))

from CORE.storage import (
    create_interview,
    get_interview,
    initialize_storage,
    list_interviews,
    save_answer,
    save_feedback,
)


class InterviewStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_directory.name)
        self.database_path = (
            self.project_root
            / "Mock_INTERVIEW"
            / "DATA"
            / "uploads"
            / "mock_buddy.sqlite3"
        )
        self.database_path.parent.mkdir(parents=True)
        initialize_storage(self.database_path)

    def tearDown(self):
        self.temp_directory.cleanup()

    def create_test_interview(self):
        return create_interview(
            resume_filename="candidate.pdf",
            resume_text="Candidate experience and skills.",
            round_key="2",
            round_name="Technical",
            questions=["Describe your project.", "How did you test it?"],
            database_path=self.database_path,
        )

    def test_interview_answers_and_feedback_persist(self):
        interview_id = self.create_test_interview()
        save_answer(interview_id, 0, "I built a web application.", self.database_path)
        save_answer(interview_id, 1, "I wrote unit tests.", self.database_path)
        save_feedback(
            interview_id,
            {
                "overall_feedback": "Clear and relevant answers.",
                "suggestions": "Add more measurable outcomes.",
                "scores_per_question": [8, 9],
                "total_score": 17,
                "raw_output": '{"scores_per_question": [8, 9]}',
            },
            self.database_path,
        )

        interview = get_interview(interview_id, self.database_path)
        self.assertEqual(interview["resume_filename"], "candidate.pdf")
        self.assertEqual(interview["resume_text"], "Candidate experience and skills.")
        self.assertEqual(interview["status"], "completed")
        self.assertEqual(interview["total_score"], 17)
        self.assertEqual(interview["max_score"], 20)
        self.assertEqual(
            [(answer["answer"], answer["score"]) for answer in interview["answers"]],
            [("I built a web application.", 8), ("I wrote unit tests.", 9)],
        )
        self.assertEqual(list_interviews(database_path=self.database_path)[0]["id"], interview_id)

    def test_answer_is_saved_before_feedback_and_in_progress_round_can_be_resumed(self):
        interview_id = self.create_test_interview()
        save_answer(interview_id, 0, "I built a web application.", self.database_path)

        interview = get_interview(interview_id, self.database_path)
        self.assertEqual(interview["status"], "in_progress")
        self.assertEqual(interview["answers"][0]["answer"], "I built a web application.")
        self.assertIsNone(interview["answers"][1]["answer"])

    def test_feedback_cannot_complete_round_with_unanswered_questions(self):
        interview_id = self.create_test_interview()
        save_answer(interview_id, 0, "I built a web application.", self.database_path)

        with self.assertRaisesRegex(ValueError, "every interview question"):
            save_feedback(
                interview_id,
                {
                    "overall_feedback": "Feedback",
                    "suggestions": "Suggestions",
                    "scores_per_question": [8, 9],
                },
                self.database_path,
            )

        interview = get_interview(interview_id, self.database_path)
        self.assertEqual(interview["status"], "in_progress")

    def test_interviews_from_previous_uploads_database_are_migrated(self):
        project_data_dir = self.project_root / "DATA"
        project_data_dir.mkdir()
        legacy_database_path = project_data_dir / self.database_path.name
        initialize_storage(legacy_database_path)
        interview_id = create_interview(
            resume_filename="existing.pdf",
            resume_text="Previously saved candidate resume.",
            round_key="1",
            round_name="HR",
            questions=["Tell me about yourself."],
            database_path=legacy_database_path,
        )

        with patch("CORE.storage.PROJECT_DATA_DIR", project_data_dir):
            initialize_storage(self.database_path)

        migrated_interview = get_interview(interview_id, self.database_path)
        self.assertIsNotNone(migrated_interview)
        self.assertEqual(migrated_interview["resume_filename"], "existing.pdf")
        self.assertEqual(migrated_interview["answers"][0]["question"], "Tell me about yourself.")

    def test_initialize_storage_creates_missing_upload_directory(self):
        database_path = (
            self.project_root
            / "fresh"
            / "Mock_INTERVIEW"
            / "DATA"
            / "uploads"
            / "mock_buddy.sqlite3"
        )

        initialize_storage(database_path)

        self.assertTrue(database_path.is_file())

    def test_interview_history_is_isolated_by_owner(self):
        interview_id = create_interview(
            resume_filename="private.pdf",
            resume_text="Private resume data.",
            round_key="1",
            round_name="HR",
            questions=["Tell me about yourself."],
            database_path=self.database_path,
            owner_id="owner-one",
        )

        self.assertEqual(
            list_interviews(database_path=self.database_path, owner_id="owner-one")[0]["id"],
            interview_id,
        )
        self.assertEqual(
            list_interviews(database_path=self.database_path, owner_id="owner-two"),
            [],
        )
        self.assertIsNone(
            get_interview(interview_id, self.database_path, owner_id="owner-two")
        )
        with self.assertRaisesRegex(ValueError, "not found or is no longer active"):
            save_answer(
                interview_id,
                0,
                "An answer from another owner.",
                self.database_path,
                owner_id="owner-two",
            )


if __name__ == "__main__":
    unittest.main()
