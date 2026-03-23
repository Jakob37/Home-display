# Repository Instructions

## Commit And Push Policy

- After completing any code or content change made by the LLM for the current task, create a git commit unless the user explicitly says not to commit.
- Only stage files changed for the current task. Do not include unrelated pre-existing modifications.
- Use a concise commit message that describes the actual change.
- Before committing, run the narrowest relevant verification available for the touched files and report any verification you could not run.
- After a successful commit, attempt to push with `git push origin HEAD` when a remote is configured.
- If push fails because of authentication, network restrictions, branch protection, or missing permissions, report that clearly and keep the local commit.

## Safety Rules

- Never revert or overwrite user changes that are unrelated to the current task.
- If the worktree already contains unrelated modifications, leave them alone and commit only the files you changed for this task.
- If a requested change is risky or ambiguous, clarify first instead of guessing.
