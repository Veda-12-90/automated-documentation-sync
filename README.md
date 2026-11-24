# Automated Documentation Sync

A beginner-friendly Python command-line tool that finds Git changes and helps a person review related documentation suggestions.

## Requirements

- Python 3
- Git
- GitHub Copilot Agent Mode in VS Code for the manual suggestion step

The tool uses only Python's built-in modules.

## Run a scan

From this repository, run:

```powershell
python docsync.py --scan-only
```

The scan lists added, modified, and deleted files and possible related Markdown and OpenAPI documents. For changed source files, it shows changed line locations without showing source-code contents.

## Review suggestions

Run the tool without `--scan-only` to review suggestions:

```powershell
python docsync.py
```

It shows the scan results and lets you enter Copilot suggestions. For each suggestion, enter a changed source reference such as `src/example.py:12` and confirm that you checked the source (or Git history for a deleted file) and that it supports the suggestion. The tool checks that the reference points to a changed line, not whether the line proves the suggestion. A person must check that; it is not automatic proof that the suggestion is correct.

The tool blocks several common password and token formats. This check can miss secrets, so review suggestions before entering them. Proposals and activity are saved together in `.docsync/records.json`. The tool does not change documentation, commit, or merge.

To run the tests:

```powershell
python -m unittest discover -s tests
```
