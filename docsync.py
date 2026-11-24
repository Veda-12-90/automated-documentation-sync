"""A small, human-reviewed documentation suggestion tool."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SOURCE_SUFFIXES = {".py", ".java", ".cs"}
MARKDOWN_SUFFIXES = {".md", ".markdown"}
OPENAPI_SUFFIXES = {".yaml", ".yml", ".json"}
IGNORED_DIRECTORIES = {
    ".git",
    ".docsync",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}
GENERIC_PATH_WORDS = {
    "src",
    "source",
    "sources",
    "docs",
    "documentation",
    "lib",
    "main",
    "test",
    "tests",
}
SENSITIVE_PATTERNS = (
    re.compile(
        r"""(?ix)
        \b(?:password|passwd|secret|api[_-]?key|access[_-]?token|
        auth[_-]?token|client[_-]?secret)\b
        \s*(?::|=|\bis\b)\s*["']?[^\s,"']{4,}
        """
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
DIFF_HUNK_PATTERN = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


class ToolError(Exception):
    """An error that can be shown to the user without a traceback."""


@dataclass(frozen=True)
class Change:
    path: str
    kind: str


@dataclass(frozen=True)
class Document:
    path: str
    kind: str


def run_git(root, arguments, binary=False):
    try:
        result = subprocess.run(
            ["git"] + arguments,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as error:
        raise ToolError("Git is not installed or is not available on PATH.") from error
    except OSError as error:
        raise ToolError("Git could not be started: " + str(error)) from error

    if result.returncode != 0:
        message = result.stderr.decode(errors="replace").strip()
        raise ToolError(message or "Git could not complete the requested operation.")

    if binary:
        return result.stdout
    return result.stdout.decode("utf-8", errors="replace").strip()


def find_repository_root(start_path):
    start_path = Path(start_path).resolve()
    if not start_path.exists() or not start_path.is_dir():
        raise ToolError("The selected project folder does not exist.")

    root_text = run_git(start_path, ["rev-parse", "--show-toplevel"])
    root = Path(root_text).resolve()
    if not root.is_dir():
        raise ToolError("Git did not return a valid project folder.")
    return root


def parse_git_status(output):
    changes = []
    records = output.split(b"\0")
    index = 0

    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4:
            raise ToolError("Git returned an unexpected change record.")

        status = record[:2].decode("ascii", errors="replace")
        path = os.fsdecode(record[3:])

        if status == "??" or "A" in status:
            kind = "added"
        elif "D" in status:
            kind = "deleted"
        else:
            kind = "modified"

        if "R" in status or "C" in status:
            index += 1

        path = Path(path).as_posix()
        if path and not path.startswith(".docsync/") and path != ".docsync":
            changes.append(Change(path=path, kind=kind))

    return changes


def get_changes(root):
    output = run_git(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        binary=True,
    )
    return parse_git_status(output)


def repository_has_head(root):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise ToolError("Git could not check the repository history.") from error

    if result.returncode not in (0, 1):
        raise ToolError("Git could not check the repository history.")
    return result.returncode == 0


def parse_evidence_ranges(diff_text, change_kind):
    ranges = []
    for line in diff_text.splitlines():
        match = DIFF_HUNK_PATTERN.match(line)
        if not match:
            continue

        if change_kind == "deleted":
            start = int(match.group(1))
            count = int(match.group(2) or "1")
        else:
            start = int(match.group(3))
            count = int(match.group(4) or "1")

        if count:
            ranges.append((start, start + count - 1))
    return ranges


def get_evidence_locations(root, source_changes):
    root = Path(root).resolve()
    has_head = repository_has_head(root)
    evidence_locations = {}

    for change in source_changes:
        ranges = []
        if has_head:
            diff_text = run_git(
                root,
                [
                    "diff",
                    "--no-ext-diff",
                    "--unified=0",
                    "HEAD",
                    "--",
                    change.path,
                ],
            )
            ranges = parse_evidence_ranges(diff_text, change.kind)

        if change.kind == "added" and not ranges:
            source_path = resolve_inside_repository(root, change.path)
            try:
                content = source_path.read_bytes()
            except OSError as error:
                raise ToolError(
                    "Could not read the added source file: " + change.path
                ) from error
            line_count = content.count(b"\n")
            if content and not content.endswith(b"\n"):
                line_count += 1
            if line_count:
                ranges = [(1, line_count)]

        evidence_locations[change.path] = ranges

    return evidence_locations


def is_source_file(path):
    return Path(path).suffix.lower() in SOURCE_SUFFIXES


def is_openapi_document(path):
    path = Path(path)
    if path.suffix.lower() not in OPENAPI_SUFFIXES:
        return False
    words = set(re.findall(r"[a-z0-9]+", path.as_posix().lower()))
    return bool(words.intersection({"api", "openapi", "swagger"}))


def path_tokens(path):
    text = Path(path).as_posix()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    return words.difference(GENERIC_PATH_WORDS)


def find_documents(root):
    root = Path(root).resolve()
    documents = []

    def report_walk_error(error):
        raise ToolError("Could not scan the selected repository: " + str(error))

    for folder, directories, filenames in os.walk(root, onerror=report_walk_error):
        directories[:] = sorted(
            name for name in directories if name not in IGNORED_DIRECTORIES
        )

        for filename in filenames:
            candidate = Path(folder) / filename
            try:
                resolved = candidate.resolve()
            except (OSError, RuntimeError) as error:
                raise ToolError("Could not check a repository file path.") from error
            try:
                relative_path = resolved.relative_to(root).as_posix()
            except ValueError:
                continue

            suffix = candidate.suffix.lower()
            if suffix in MARKDOWN_SUFFIXES:
                documents.append(Document(relative_path, "Markdown"))
            elif is_openapi_document(candidate):
                documents.append(Document(relative_path, "OpenAPI"))

    return sorted(documents, key=lambda document: document.path.lower())


def find_related_documents(changes, documents):
    related = {}
    source_changes = [change for change in changes if is_source_file(change.path)]

    for change in source_changes:
        source_words = path_tokens(change.path)
        matches = [
            document
            for document in documents
            if source_words.intersection(path_tokens(document.path))
        ]
        related[change.path] = matches

    return related


def resolve_inside_repository(root, value):
    root = Path(root).resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate

    try:
        resolved = candidate.resolve()
        relative = resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise ToolError("The file path must stay inside the selected repository.") from error

    if relative == Path("."):
        raise ToolError("A file path is required, not the repository folder.")
    return resolved


def validate_document_target(root, value):
    target = resolve_inside_repository(root, value)
    if target.suffix.lower() not in MARKDOWN_SUFFIXES.union(OPENAPI_SUFFIXES):
        raise ToolError("The target must be a Markdown or OpenAPI document.")
    if target.suffix.lower() in OPENAPI_SUFFIXES and not is_openapi_document(target):
        raise ToolError("The YAML or JSON target must have an API-related name.")
    return target.relative_to(Path(root).resolve()).as_posix()


def validate_evidence_reference(root, value, evidence_locations):
    try:
        path_value, line_value = value.rsplit(":", 1)
        line_number = int(line_value)
    except (ValueError, AttributeError) as error:
        raise ToolError("Enter an evidence reference as file-path:line-number.") from error

    if line_number < 1:
        raise ToolError("The evidence line number must be positive.")

    evidence_path = resolve_inside_repository(root, path_value)
    relative_path = evidence_path.relative_to(Path(root).resolve()).as_posix()
    valid_ranges = evidence_locations.get(relative_path, [])
    if not any(start <= line_number <= end for start, end in valid_ranges):
        raise ToolError(
            "Choose a changed line from a changed Python, Java, or C# source file."
        )
    return "{0}:{1}".format(relative_path, line_number)


def contains_sensitive_information(value):
    return any(pattern.search(value) for pattern in SENSITIVE_PATTERNS)


def print_scan_summary(changes, related_documents, evidence_locations):
    print("\nGit changes:")
    if not changes:
        print("  No changed files found.")
    else:
        for change in changes:
            print("  {0:8} {1}".format(change.kind, change.path))

    source_changes = [change for change in changes if is_source_file(change.path)]
    unsupported = [
        change
        for change in changes
        if not is_source_file(change.path)
        and Path(change.path).suffix.lower() not in MARKDOWN_SUFFIXES
        and not is_openapi_document(change.path)
    ]

    if unsupported:
        print("\nChanged files this version does not analyze:")
        for change in unsupported:
            print("  " + change.path)

    print("\nPossible related documentation:")
    if not source_changes:
        print("  No changed Python, Java, or C# files were found.")
    else:
        for change in source_changes:
            matches = related_documents.get(change.path, [])
            print("  Source: " + change.path)
            ranges = evidence_locations.get(change.path, [])
            if ranges:
                locations = [
                    "{0}:{1}".format(change.path, start)
                    if start == end
                    else "{0}:{1}-{2}".format(change.path, start, end)
                    for start, end in ranges
                ]
                print("    Changed lines: " + ", ".join(locations))
            else:
                print("    No changed source lines were found.")
            if matches:
                for document in matches:
                    print("    {0}: {1}".format(document.kind, document.path))
            else:
                print("    No possible match found.")

    print("\nThe summary uses file names and evidence locations only; it does not show source-code lines.")


def load_record_store(root):
    path = resolve_inside_repository(root, Path(".docsync") / "records.json")
    if not path.exists():
        return {"proposals": [], "activity": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ToolError("Could not read .docsync/records.json.") from error

    if not isinstance(data, dict):
        raise ToolError(".docsync/records.json must contain a JSON object.")
    for section in ("proposals", "activity"):
        records = data.get(section)
        if not isinstance(records, list) or any(
            not isinstance(item, dict) for item in records
        ):
            raise ToolError(
                ".docsync/records.json must contain proposal and activity lists."
            )
    return data


def save_record_store(root, record_store):
    directory = resolve_inside_repository(root, ".docsync")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ToolError("Could not create the .docsync folder.") from error
    path = resolve_inside_repository(root, Path(".docsync") / "records.json")
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(directory),
            prefix=".records-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(record_store, temporary_file, indent=2, ensure_ascii=False)
            temporary_file.write("\n")
        os.replace(str(temporary_path), str(path))
    except OSError as error:
        if temporary_path is not None:
            try:
                if temporary_path.exists():
                    temporary_path.unlink()
            except OSError as cleanup_error:
                raise ToolError(
                    "Could not save .docsync/records.json or remove its temporary file."
                ) from cleanup_error
        raise ToolError("Could not save .docsync/records.json.") from error


def add_proposals(root, source_changes, evidence_locations):
    if not source_changes:
        print("\nSuggestions need a changed Python, Java, or C# file as evidence.")
        return

    record_store = load_record_store(root)
    initial_proposal_count = len(record_store["proposals"])

    print("\nUse Copilot Agent Mode in VS Code, then return here.")
    print("Enter a short suggestion summary. Do not paste raw source-code lines.")

    while True:
        try:
            answer = input("\nAdd a suggestion? [y/N] ").strip().lower()
        except EOFError:
            print_review_summary(record_store, initial_proposal_count)
            return
        if answer not in {"y", "yes"}:
            print_review_summary(record_store, initial_proposal_count)
            return

        try:
            target_input = input("Target Markdown/OpenAPI file: ").strip()
            target = validate_document_target(root, target_input)
            evidence_input = input(
                "Changed source evidence (file path and line number): "
            ).strip()
            evidence = validate_evidence_reference(
                root, evidence_input, evidence_locations
            )
            suggestion = input("Short suggested update (no source code): ").strip()
        except EOFError:
            print("\nInput ended; no suggestion was saved.")
            return
        except ToolError as error:
            print("Suggestion not accepted: " + str(error))
            continue

        if not suggestion:
            print("Suggestion not accepted: enter a short update summary.")
            continue

        if contains_sensitive_information(suggestion):
            print(
                "Suggestion not accepted: it may contain a password, token, or other secret. "
                "Remove the sensitive value and try again."
            )
            continue

        try:
            evidence_confirmation = input(
                "Have you checked this source file (or Git history if deleted) "
                "and confirmed it supports the suggestion? [y/N] "
            ).strip().lower()
            if evidence_confirmation not in {"y", "yes"}:
                print("Suggestion not saved. Check its source evidence first.")
                continue

            confirmation = input(
                "Have you checked the suggestion for sensitive information? [y/N] "
            ).strip().lower()
        except EOFError:
            print("\nInput ended; no suggestion was saved.")
            return
        if confirmation not in {"y", "yes"}:
            print("Suggestion not saved. Check it before continuing.")
            continue

        print("\nProposal for {0}: {1}".format(target, suggestion))
        print("Evidence reference: " + evidence)
        try:
            decision = input("Approve this proposal? [y/N] ").strip().lower()
        except EOFError:
            print("\nInput ended; no decision was saved.")
            return
        decision = "approved" if decision in {"y", "yes"} else "rejected"
        timestamp = datetime.now(timezone.utc).isoformat()
        proposal_id = str(uuid.uuid4())

        record_store["proposals"].append(
            {
                "proposal_id": proposal_id,
                "target_document": target,
                "suggestion": suggestion,
                "evidence_reference": evidence,
                "decision": decision,
                "created_at": timestamp,
            }
        )
        record_store["activity"].append(
            {
                "proposal_id": proposal_id,
                "action": decision,
                "created_at": timestamp,
            }
        )
        save_record_store(root, record_store)
        print("Decision recorded as {0}. No document was changed.".format(decision))


def print_review_summary(record_store, initial_proposal_count):
    new_proposals = record_store["proposals"][initial_proposal_count:]
    approved = sum(
        proposal.get("decision") == "approved" for proposal in new_proposals
    )
    rejected = sum(
        proposal.get("decision") == "rejected" for proposal in new_proposals
    )
    print(
        "\nReview summary: {0} proposal(s), {1} approved, {2} rejected.".format(
            len(new_proposals), approved, rejected
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find changed source files and review documentation suggestions."
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Project repository folder (defaults to the current folder).",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Show changed files and stop without asking for suggestions.",
    )
    args = parser.parse_args(argv)

    try:
        root = find_repository_root(args.repo)
        changes = get_changes(root)
        source_changes = [change for change in changes if is_source_file(change.path)]
        evidence_locations = get_evidence_locations(root, source_changes)
        documents = find_documents(root)
        related_documents = find_related_documents(changes, documents)

        print("Repository scan complete.")
        print_scan_summary(changes, related_documents, evidence_locations)

        if args.scan_only:
            return 0
        add_proposals(root, source_changes, evidence_locations)
        return 0
    except ToolError as error:
        print("Error: " + str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped by the user.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
