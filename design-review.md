# Design Review: Automated Documentation Sync

## Review Scope

This review compares `architecture.md` with `requirements.md`. It checks whether the architecture is clear, complete, and suitable for a beginner project.

## Review Summary

The architecture covers the main requirements: Git change detection, supported source and documentation files, Copilot suggestions, evidence checks, human review, JSON records, safety, and error handling.

No base-branch and feature-branch comparison is added because it is not required by `requirements.md`.

## Findings and Updates

### DR-01: Copilot handoff was unclear

- **Finding:** The architecture said that the person returns suggestions to the tool but did not explain how.
- **Decision:** The person copies the evidence summary into Copilot Agent Mode and copies its suggestions back into the tool.
- **Update:** Clarified the handoff in `architecture.md`.

### DR-02: Deleted source-file handling needed to be clearer

- **Finding:** The architecture said documentation would not be deleted, but did not clearly say that related documentation is shown for human review.
- **Decision:** Show potentially related documentation for human review and never delete it automatically.
- **Update:** Clarified this in `architecture.md`.

### DR-03: Terminal summary and JSON record contents needed clarification

- **Finding:** The architecture did not clearly say that the terminal shows a proposal summary or what each JSON record contains.
- **Decision:** Show proposals and a summary in the terminal. Proposal records store suggestions and evidence references; activity records store review decisions.
- **Update:** Clarified this in `architecture.md`.

### DR-04: Sensitive information in suggestions

- **Finding:** A person could enter a Copilot suggestion that contains a password or token.
- **Decision:** Check suggestions for common password and token patterns and reject likely matches. The check is limited, so the person must still review text before entering it.
- **Update:** Added the check and its limitation to `architecture.md`, `impl-plan.md`, and `README.md`.

### DR-05: Proposal and activity records could get out of sync

- **Finding:** Saving proposals and activity to separate files could leave only one updated if a save fails.
- **Decision:** Store both lists in one JSON file and replace that file as a single operation.
- **Update:** Updated the storage description in `architecture.md`, `impl-plan.md`, and `README.md`.

### DR-06: Evidence references did not identify changed lines

- **Finding:** A file-only reference did not point to the changed part of the source.
- **Decision:** Show and validate changed line locations. The person inspects the source (or Git history for a deleted file) and confirms support. The tool does not claim to verify the meaning of the suggestion.
- **Update:** Added changed-line references and clarified this limit in the implementation and project documentation.

## Design Decisions Confirmed

- GitHub Copilot Agent Mode is used by a person in VS Code; the tool does not connect to Copilot automatically.
- Evidence checks confirm that suggestions refer to a changed line but do not guarantee correctness.
- A person inspects source content; the tool validates the changed-line reference only.
- A human makes the final decision on each suggestion.
- Approval does not automatically apply changes. The tool does not automatically delete documentation, commit, or merge.
- Proposal and activity information is stored as JSON inside the selected repository.
- Summaries and JSON records use evidence references, not raw source-code lines. A person confirms whether suggestions are supported; this is not automatic proof.
- The tool checks common password and token patterns but may miss sensitive information.
- Proposals and activity are saved together in `.docsync/records.json`.
