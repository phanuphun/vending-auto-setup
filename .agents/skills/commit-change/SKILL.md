---
name: commit-change
description: Commit staged, modified, or untracked changes in the current repository or a named sub-project with a suitable Conventional Commit message. Use when the user asks to commit changes, create a git commit, run commit-change, or decide whether a change should include [skip ci].
---

# Commit Change

Create a focused git commit for the current repository or the sub-project named by the user. Preserve unrelated user changes and avoid staging anything suspicious.

## Workflow

1. Identify the repository.
   - If the user provides a sub-project name or path, switch to that directory.
   - Otherwise use the current working directory or the repository most recently discussed.
   - Run `git status --short`.
   - If there are no changes, report that there is nothing to commit and stop.

2. Inspect the change.
   - Review changed and untracked paths before staging.
   - For modified tracked files, inspect the diff with `git diff -- <path>`.
   - For staged files, inspect with `git diff --cached -- <path>`.
   - For untracked files, read only enough to understand whether they should be committed.
   - Do not stage files that appear to contain secrets, credentials, local environment values, generated junk, or unrelated work. Warn the user when these appear.

3. Decide whether to include `[skip ci]`.
   - Include `[skip ci]` when all changed files are documentation or non-build assets:
     - `*.md`
     - `documents/**`
     - `*.txt`
     - `*.png`, `*.jpg`, `*.jpeg`, `*.svg`
     - `LICENSE`, `NOTICE`
   - Include `[skip ci]` for central/deploy repositories when the repository name contains `deploy` or `central` and the changed files are only deployment or documentation files:
     - `docker-compose.yml`
     - `.gitlab-ci.yml`
     - `*.env.example`
     - `README.md`, `*.md`
   - Do not include `[skip ci]` when source, package metadata, migrations, tests, CI behavior, or runtime configuration may need a pipeline.
   - Never commit real `.env` files or credential files just to satisfy the deploy rule.

4. Stage intentionally.
   - Prefer `git add -- <path>` for each intended file.
   - Avoid `git add .` and `git add -A` unless the user explicitly asked for a broad commit and the status has been reviewed.
   - Re-run `git status --short` after staging.

5. Match the repository's commit style.
   - Run `git log --oneline -5` when history is available.
   - Prefer Conventional Commits unless the recent history clearly uses another style.
   - Choose the narrowest suitable type:
     - `fix`: bug fix
     - `feat`: new feature
     - `docs`: documentation-only change
     - `chore`: tooling, config, CI, generated maintenance, or build scripts
     - `refactor`: code restructure without behavior change
     - `test`: tests only
   - Use a concise scope when it helps, such as a package, app, service, or feature name.

6. Commit.
   - Use a commit message file or another shell-safe method for multiline messages.
   - Message shape:

```text
<type>(<scope>): <short description>

<optional body explaining why, only when useful>

[skip ci]

Co-authored-by: Codex <noreply@anthropic.com>
```

   - Omit the scope when it would be noisy.
   - Omit the body when the subject is enough.
   - Include `[skip ci]` only when step 3 says to include it.
   - Include the co-author trailer only when the repository convention or user preference expects AI co-author trailers.

7. Report the result.
   - Show the commit hash and subject.
   - State whether `[skip ci]` was applied and why.
   - Mention any files that were intentionally left unstaged.
