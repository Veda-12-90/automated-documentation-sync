import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docsync import (
    Change,
    Document,
    ToolError,
    add_proposals,
    contains_sensitive_information,
    find_documents,
    find_related_documents,
    get_changes,
    get_evidence_locations,
    is_openapi_document,
    is_source_file,
    load_record_store,
    parse_git_status,
    resolve_inside_repository,
    save_record_store,
    validate_evidence_reference,
)


class GitStatusTests(unittest.TestCase):
    def test_parse_added_modified_and_deleted_paths(self):
        output = (
            b"?? new file.py\0"
            b" M src/Changed.java\0"
            b" D src/Removed.cs\0"
        )

        changes = parse_git_status(output)

        self.assertEqual(
            changes,
            [
                Change("new file.py", "added"),
                Change("src/Changed.java", "modified"),
                Change("src/Removed.cs", "deleted"),
            ],
        )

    def test_internal_records_are_not_reported_as_project_changes(self):
        changes = parse_git_status(b"?? .docsync/activity.json\0")

        self.assertEqual(changes, [])


class MatchingTests(unittest.TestCase):
    def test_source_and_openapi_file_types_are_recognized(self):
        self.assertTrue(is_source_file("src/Example.PY"))
        self.assertTrue(is_source_file("src/Example.java"))
        self.assertTrue(is_source_file("src/Example.cs"))
        self.assertTrue(is_openapi_document("specs/openapi.yaml"))
        self.assertFalse(is_openapi_document("settings.json"))

    def test_related_document_is_matched_by_name(self):
        changes = [Change("src/payments/InvoiceService.java", "modified")]
        documents = [
            Document("docs/invoice-service.md", "Markdown"),
            Document("specs/openapi.yaml", "OpenAPI"),
        ]

        related = find_related_documents(changes, documents)

        self.assertEqual(
            [document.path for document in related["src/payments/InvoiceService.java"]],
            ["docs/invoice-service.md"],
        )

    def test_unrelated_document_is_not_matched(self):
        related = find_related_documents(
            [Change("src/billing/BillingService.py", "modified")],
            [Document("docs/user-guide.md", "Markdown")],
        )

        self.assertEqual(related["src/billing/BillingService.py"], [])


class SensitiveInformationTests(unittest.TestCase):
    def test_detects_common_secret_patterns_without_echoing_values(self):
        self.assertTrue(contains_sensitive_information("api_key = 'abcd1234secret'"))
        self.assertTrue(contains_sensitive_information("Authorization: Bearer abcdef1234567890"))
        self.assertTrue(contains_sensitive_information("github_pat_abcdefghijklmnopqrstuvwxyz123456"))

    def test_normal_suggestion_text_is_not_flagged(self):
        self.assertFalse(
            contains_sensitive_information("Update the API key setup instructions.")
        )


class RepositoryBoundaryTests(unittest.TestCase):
    def test_path_outside_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            with self.assertRaises(ToolError):
                resolve_inside_repository(root, "../outside.txt")

    def test_only_changed_source_paths_can_be_used_as_evidence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            evidence = validate_evidence_reference(
                root,
                "src/Changed.py:5",
                {"src/Changed.py": [(3, 7)]},
            )

            self.assertEqual(evidence, "src/Changed.py:5")

            with self.assertRaises(ToolError):
                validate_evidence_reference(
                    root,
                    "src/Changed.py:8",
                    {"src/Changed.py": [(3, 7)]},
                )

    def test_evidence_reference_outside_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            with self.assertRaises(ToolError):
                validate_evidence_reference(
                    root,
                    "../outside.py:3",
                    {"../outside.py": [(3, 3)]},
                )


class RecordStoreTests(unittest.TestCase):
    def test_record_store_is_saved_and_loaded_as_one_json_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            store = {
                "proposals": [{"proposal_id": "p1"}],
                "activity": [{"proposal_id": "p1", "action": "approved"}],
            }

            save_record_store(root, store)

            saved_path = root / ".docsync" / "records.json"
            self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8")), store)
            self.assertEqual(load_record_store(root), store)
            self.assertEqual(
                [path.name for path in (root / ".docsync").iterdir()],
                ["records.json"],
            )

    def test_invalid_record_store_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            record_directory = root / ".docsync"
            record_directory.mkdir()
            (record_directory / "records.json").write_text(
                '{"proposals": [], "activity": "not a list"}',
                encoding="utf-8",
            )

            with self.assertRaises(ToolError):
                load_record_store(root)

    def test_failed_replace_keeps_existing_record_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            original = {"proposals": [], "activity": []}
            save_record_store(root, original)
            replacement = {
                "proposals": [{"proposal_id": "p1"}],
                "activity": [{"proposal_id": "p1", "action": "approved"}],
            }

            with patch("docsync.os.replace", side_effect=PermissionError):
                with self.assertRaises(ToolError):
                    save_record_store(root, replacement)

            self.assertEqual(load_record_store(root), original)
            self.assertEqual(
                [path.name for path in (root / ".docsync").iterdir()],
                ["records.json"],
            )

    def test_review_records_decision_without_changing_document(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "src" / "Example.py"
            document = root / "docs" / "Example.md"
            source.parent.mkdir()
            document.parent.mkdir()
            source.write_text("value = 1\n", encoding="utf-8")
            document.write_text("# Existing documentation\n", encoding="utf-8")
            original_document = document.read_text(encoding="utf-8")

            answers = [
                "y",
                "docs/Example.md",
                "src/Example.py:1",
                "Add a short example.",
                "y",
                "y",
                "y",
                "y",
                "docs/Example.md",
                "src/Example.py:1",
                "Add a link to the example.",
                "y",
                "y",
                "n",
                "n",
            ]
            with patch("builtins.input", side_effect=answers):
                with patch("builtins.print") as print_mock:
                    add_proposals(
                        root,
                        [Change("src/Example.py", "added")],
                        {"src/Example.py": [(1, 1)]},
                    )

            store = load_record_store(root)
            self.assertEqual(store["proposals"][0]["decision"], "approved")
            self.assertEqual(store["activity"][0]["action"], "approved")
            self.assertEqual(store["proposals"][1]["decision"], "rejected")
            self.assertEqual(store["activity"][1]["action"], "rejected")
            self.assertEqual(document.read_text(encoding="utf-8"), original_document)
            printed_text = " ".join(
                str(call.args[0]) for call in print_mock.call_args_list if call.args
            )
            self.assertIn("2 proposal(s), 1 approved, 1 rejected", printed_text)

    def test_suspected_secret_is_not_printed_or_saved(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "Example.py").write_text("value = 1\n", encoding="utf-8")
            answers = [
                "y",
                "Example.md",
                "Example.py",
                "api_key = 'abcd1234secret'",
                "n",
            ]

            with patch("builtins.input", side_effect=answers):
                with patch("builtins.print") as print_mock:
                    add_proposals(
                        root,
                        [Change("Example.py", "added")],
                        {"Example.py": [(1, 1)]},
                    )

            printed_text = " ".join(
                str(call.args[0]) for call in print_mock.call_args_list if call.args
            )
            self.assertNotIn("abcd1234secret", printed_text)
            self.assertFalse((root / ".docsync" / "records.json").exists())


class GitIntegrationTests(unittest.TestCase):
    def test_real_repository_reports_added_modified_and_deleted_source_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Test User"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "test@example.com"],
                check=True,
                capture_output=True,
            )

            (root / "Example.py").write_text(
                "first = 1\nvalue = 1\n", encoding="utf-8"
            )
            (root / "Removed.java").write_text(
                "class Removed {}\n// old\n", encoding="utf-8"
            )
            (root / "Keep.cs").write_text("class Keep {}\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "."],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-m", "initial"],
                check=True,
                capture_output=True,
            )

            (root / "Example.py").write_text(
                "first = 1\nvalue = 2\n", encoding="utf-8"
            )
            (root / "Added.cs").write_text("class Added {}\n", encoding="utf-8")
            (root / "Removed.java").unlink()
            (root / "docs").mkdir()
            (root / "docs" / "Example.md").write_text("# Example\n", encoding="utf-8")

            changes = get_changes(root)
            kinds = {change.path: change.kind for change in changes}
            self.assertEqual(kinds["Example.py"], "modified")
            self.assertEqual(kinds["Added.cs"], "added")
            self.assertEqual(kinds["Removed.java"], "deleted")

            source_changes = [
                change for change in changes if is_source_file(change.path)
            ]
            evidence_locations = get_evidence_locations(root, source_changes)
            self.assertEqual(evidence_locations["Example.py"], [(2, 2)])
            self.assertEqual(evidence_locations["Added.cs"], [(1, 1)])
            self.assertEqual(evidence_locations["Removed.java"], [(1, 2)])

            related = find_related_documents(changes, find_documents(root))
            self.assertEqual(
                [document.path for document in related["Example.py"]],
                ["docs/Example.md"],
            )

    def test_untracked_source_in_repository_without_commit_gets_line_locations(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            (root / "New.py").write_text("first = 1\nsecond = 2\n", encoding="utf-8")

            changes = get_changes(root)
            evidence_locations = get_evidence_locations(
                root,
                [change for change in changes if is_source_file(change.path)],
            )

            self.assertEqual(evidence_locations["New.py"], [(1, 2)])


if __name__ == "__main__":
    unittest.main()
