# Implementation Plan: Automated Documentation Sync

## Goal

Build the Python command-line tool in small steps. Each task has a clear result and depends only on earlier tasks.

## Task Order

### IP-01: Create the command-line starting point

- **Priority:** High
- **Depends on:** None
- **Work:** Create the basic Python command-line program. Let the user select a project repository and make sure file access stays inside it.
- **Done when:** The program starts and clearly reports an invalid or missing repository.

### IP-02: Find Git changes

- **Priority:** High
- **Depends on:** IP-01
- **Work:** Use Git to list added, modified, and deleted files.
- **Done when:** The program reports each changed file and its change type.

### IP-03: Find changed source lines

- **Priority:** High
- **Depends on:** IP-02
- **Work:** Identify changed Python, Java, and C# files and their changed line locations. The person inspects actual source content; the tool does not display raw source-code lines.
- **Done when:** Changed source files and line locations are listed, and missing or unsupported files are clearly reported.

### IP-04: Find related documentation

- **Priority:** High
- **Depends on:** IP-02
- **Work:** Find Markdown and OpenAPI files that may relate to changed source files. For deleted source files, list possible related documents without deleting them.
- **Done when:** The program displays possible documentation matches for human review.

### IP-05: Prepare an evidence summary

- **Priority:** High
- **Depends on:** IP-03 and IP-04
- **Work:** Prepare a short summary of changed files, changed line locations, and possible documentation matches without showing raw source-code lines.
- **Done when:** The summary clearly labels documentation matches as possible and does not present source-code claims as automatically verified.

### IP-06: Add the Copilot handoff

- **Priority:** High
- **Depends on:** IP-05
- **Work:** Show the evidence references. The person checks the relevant files in VS Code, shares only needed information without sensitive values with Copilot Agent Mode, and brings suggestions back into the tool.
- **Done when:** The person can provide suggestions without an automatic Copilot connection.

### IP-07: Check suggestions against evidence

- **Priority:** High
- **Depends on:** IP-05 and IP-06
- **Work:** Check that each suggestion refers to a changed source line. Ask the person to inspect the source (or Git history for a deleted file) and confirm that it supports the suggestion.
- **Done when:** The evidence reference is a changed line and human-confirmed. The tool clearly says this does not automatically prove correctness.

### IP-08: Add human review and a summary

- **Priority:** High
- **Depends on:** IP-07
- **Work:** Show each proposal and a summary in the terminal. The person checks suggestions for sensitive values before approving or rejecting them.
- **Done when:** The person makes the final decision, and approval alone does not apply changes.

### IP-09: Save proposal and activity records

- **Priority:** High
- **Depends on:** IP-08
- **Work:** After human review, save suggestions, evidence references, and review decisions together in `.docsync/records.json` inside the selected repository. Do not save raw source-code lines.
- **Done when:** The JSON file contains separate proposal and activity lists and can be safely replaced as one complete file.

### IP-10: Check errors and safety rules

- **Priority:** High
- **Depends on:** IP-01 through IP-09
- **Work:** Check handling of Git errors, missing files, unsupported files, repository boundaries, and common password/token patterns. Confirm that documentation is not deleted and changes are not automatically applied, committed, or merged.
- **Done when:** Errors are clear, files outside the selected repository are not accessed, and the safety rules hold. Document that pattern checks may miss sensitive information.

### IP-11: Run basic end-to-end checks

- **Priority:** High
- **Depends on:** IP-10
- **Work:** Test a real temporary Git repository with added, modified, and deleted source files, related documentation, evidence checks, sensitive-text checks, and JSON records.
- **Done when:** The tool produces a summary, records human decisions, and saves valid records without changing documentation, deleting files, committing, or merging.

## Blocked Work

- No tasks are currently blocked by a design decision. Evidence support is confirmed by the person, and the tool checks common secret patterns as a limited extra safeguard. The person still reviews suggestions because pattern checks can miss sensitive information.
