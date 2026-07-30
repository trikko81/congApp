---
name: gitWorker
description: Automates staging, committing, and pushing code changes whenever significant file edits or code block updates occur.
---

# 🐙 GitWorker Skill

This skill defines the process for automatically staging, committing, and pushing repository changes after code modifications.

## Workflow

Whenever code modifications, new file additions, or structural updates are completed:

1. **Check Status**:
   Run `git status` to identify modified and untracked files.

2. **Stage Changes**:
   Stage the relevant modified files (or use targeted `git add <filepath>`):
   ```bash
   git add .
   ```

3. **Format Commit Message**:
   Write a concise, descriptive commit message following conventional commit guidelines:
   - `feat(...)`: For net-new features
   - `fix(...)`: For bug fixes or corrections
   - `docs(...)`: For markdown/documentation updates
   - `refactor(...)`: For structural code adjustments

   Example:
   ```bash
   git commit -m "feat(rag): add layout-aware PyMuPDF chunking pipeline"
   ```

4. **Push Changes**:
   Push committed changes to the active branch on origin:
   ```bash
   git push
   ```

> [!NOTE]
> If a push is rejected due to remote changes, pull with rebase (`git pull --rebase origin <branch>`) before pushing again.
