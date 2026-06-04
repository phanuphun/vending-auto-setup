---
description: Run the commit-change workflow from .claude/skills
argument-hint: [sub-project]
allowed-tools: Read, Glob, Grep, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git commit:*)
---

Read and follow the commit-change skill at:

`@.claude/skills/commit-change/SKILL.md`

Use `$ARGUMENTS` as the optional sub-project name or path.
