# Architecture: Automated Documentation Sync

## 1. Overview

The tool is a Python command-line program. It uses Git to find changed files, looks for related documentation, and prepares changed-line references to support suggested updates. It does not put raw source-code lines in its summaries or JSON records.

A person checks the relevant source files, shares only needed information with GitHub Copilot Agent Mode in VS Code, and checks suggestions before returning them to the tool. A person reviews every suggestion. The tool does not automatically change or delete documentation, commit, or merge.

## 2. Component Diagram

```text
Developer
   |
   v
Python command-line tool <----> Git
   |
   +--> Find changed source files
   |
   +--> Find related Markdown and OpenAPI files
   |
   v
Evidence summary
   |
   v
Person checks the summary, then shares it with Copilot Agent Mode in VS Code
   |
   v
Person copies suggestions back into the tool
   |
   v
Evidence check and human review
   |
   v
JSON proposal and activity records
```

## 3. Main Parts

- **Python command-line tool:** Runs the steps and shows results and errors in the terminal.
- **Git:** Reports added, modified, and deleted files.
- **Source and documentation finder:** Identifies changed Python, Java, and C# files and their changed line locations, then finds potentially related Markdown and OpenAPI files. It reports references, not source-code lines. The person opens the source file (or Git history for a deleted file) to check the actual evidence.
- **Copilot Agent Mode:** Suggests documentation updates using evidence the person copies into VS Code.
- **Evidence check and review:** Checks that a suggestion refers to a changed source line. The person confirms that the source (or Git history for a deleted file) supports the suggestion, then approves or rejects it. This human check does not guarantee correctness.
- **JSON records:** `.docsync/records.json` stores proposals and activity in separate lists. It is saved as one file so the two lists stay together. Records contain suggestions and evidence references, not raw source-code lines.

## 4. Technology Choices

- Use Python for the command-line tool.
- Use the installed Git command-line program to read Git changes.
- Use Python's built-in file and JSON features to avoid extra packages.
- Use GitHub Copilot Agent Mode in VS Code through a person. The tool does not connect to Copilot automatically.
- Store proposal and activity records in JSON files.

## 5. How It Works

1. The person runs the tool from a selected project repository.
2. The tool asks Git for added, modified, and deleted files.
3. The tool lists changed Python, Java, and C# files and their changed line locations, then finds possible related documentation. It does not show source-code lines.
4. The tool shows file names and changed-line locations in a summary.
5. The person checks the relevant source files in VS Code and shares only needed information, without sensitive values, with Copilot Agent Mode.
6. The person checks Copilot's suggestions for sensitive information and returns them to the tool.
7. The tool checks that the evidence reference points to a changed source line. The person opens the source (or Git history for a deleted file) and confirms that it supports the suggestion.
8. The tool checks suggestions for several common password and token formats, then shows proposals for human approval or rejection. This check may miss sensitive information.
9. The tool saves proposals and activity together in `.docsync/records.json`. It does not apply the proposed documentation changes.

## 6. Safety and Errors

- The tool only reads and writes files inside the selected repository.
- Terminal summaries, logs, and JSON records do not contain raw source-code lines.
- The tool blocks several common password and token formats in suggestions. This check is limited and may miss sensitive information, so the person must also review source files before sharing and suggestions before returning them to the tool.
- The tool finds changed line locations but does not interpret source-code meaning. The person reviews whether a suggestion is supported by its source reference. The tool does not claim that this confirmation proves the suggestion is correct.
- When a source file is deleted, the tool finds potentially related documentation and shows it for human review. It never deletes documentation.
- If the person does not confirm that a suggestion is supported by its evidence, the tool does not save it.
- Evidence checks do not guarantee that a suggestion is correct. A person makes the final decision.
- Approval does not apply changes. Applying a suggestion, if supported later, requires a separate action.
- The tool never commits or merges changes.
- The tool clearly reports Git errors, missing files, and unsupported file types.
- The tool rejects suggestions that match known password or token patterns, but this check cannot detect every sensitive value.
