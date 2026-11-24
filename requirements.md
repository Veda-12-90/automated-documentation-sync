# Automated Documentation Sync Requirements

## 1. Project Overview

Automated Documentation Sync is a Python-based tool for helping keep project documentation in step with source-code changes. It uses Git to find changed files and GitHub Copilot Agent Mode to suggest documentation updates. Suggestions are checked and shown to a person for review. The tool does not commit or merge changes.

## 2. Project Objectives

- **OBJ-01:** Find added, modified, and deleted files in a Git repository.
- **OBJ-02:** Identify Markdown and OpenAPI documentation that may relate to changed source files.
- **OBJ-03:** Suggest evidence-based documentation updates.
- **OBJ-04:** Make proposed updates easy for a person to review and accept or reject.
- **OBJ-05:** Keep a record of proposals and activity.

## 3. Functional Requirements

- **FR-01:** The system shall use Git to detect added, modified, and deleted files.
- **FR-02:** The system shall identify changed line locations in Python, Java, and C# source files.
- **FR-03:** The system shall identify Markdown and OpenAPI documentation that may be affected by source-code changes.
- **FR-04:** The system shall use GitHub Copilot Agent Mode to suggest documentation updates.
- **FR-05:** Each suggestion shall include a reference to changed source-code line locations. A human shall confirm that the referenced source supports the suggestion.
- **FR-06:** If a human cannot confirm the source evidence, the system shall report the limitation and shall not save the suggestion as approved.
- **FR-07:** The system shall check that each evidence reference points to a changed source-code line and shall ask a human to confirm that the line supports the suggestion.
- **FR-08:** The system shall show proposed changes and a summary in the terminal.
- **FR-09:** A human shall make the final decision to approve or reject each proposed change. Approval alone shall not apply, commit, or merge a proposal. If applying an approved proposal is supported, it shall require a separate, explicit human action.
- **FR-10:** The system shall store proposal and activity information in JSON files.
- **FR-11:** The system shall clearly report errors and unsupported files.
- **FR-12:** The system shall not automatically commit or merge changes.
- **FR-13:** When a source-code file is deleted, the system shall identify potentially related documentation for human review and shall not automatically delete that documentation.

## 4. Non-Functional Requirements

- **NFR-01:** The system shall use simple, clear messages that are suitable for beginner users.
- **NFR-02:** The system shall report errors without presenting failed work as successful.
- **NFR-03:** The system shall keep suggestions understandable and linked to the source-code evidence that supports them.
- **NFR-04:** The system shall leave final documentation decisions under human control.
- **NFR-05:** The system shall reject suggestions that match known common password or token patterns and ask a human to check for other sensitive information. This check may not detect every sensitive value.
- **NFR-06:** The system shall only access files within the selected project repository.

## 5. Project Scope

### In scope

- Git-based detection of added, modified, and deleted files.
- Identification of changed line locations in Python, Java, and C# source files.
- Identification of related Markdown and OpenAPI documentation.
- AI-assisted documentation suggestions using GitHub Copilot Agent Mode.
- Changed-line references, human confirmation of evidence, a summary, and terminal-based review.
- JSON records of proposals and activity.
- Clear handling of errors and unsupported files.

### Out of scope

- Automatically committing or merging changes.
- Making unsupported or invented technical claims.
- Designing or implementing the system architecture.
- Implementing the tool as part of this requirements step.

## 6. Acceptance Criteria

- **AC-01:** Given a Git repository with added, modified, or deleted files, the system identifies the changed files and their change types.
- **AC-02:** The system identifies changed line locations in Python, Java, and C# files and lists potentially related Markdown and OpenAPI documentation.
- **AC-03:** The system uses GitHub Copilot Agent Mode to propose relevant documentation updates.
- **AC-04:** Each suggestion has a reference to changed source lines. A human confirms that the source supports it. If the human cannot confirm this, the system reports the limitation and does not save it as approved.
- **AC-05:** Before review, the system checks that each evidence reference points to a changed source line and asks a human to confirm that the line supports the suggestion.
- **AC-06:** The system shows the proposals and a summary in the terminal and lets a person approve or reject proposals.
- **AC-07:** The system records proposal and activity information in JSON files.
- **AC-08:** Unsupported files and processing errors are clearly reported.
- **AC-09:** The system does not commit or merge changes automatically.
- **AC-10:** When a source-code file is deleted, the system identifies potentially related documentation for human review and does not automatically delete it.
- **AC-11:** A human makes the final decision on each proposal. Approval does not apply, commit, or merge a proposal, and applying an approved proposal, if supported, requires a separate, explicit human action.
- **AC-12:** The system rejects suggestions that match its common password or token patterns and asks a human to check for other sensitive information. The pattern check may miss sensitive values.
- **AC-13:** The system accesses files only within the selected project repository.
