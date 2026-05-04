---
name: update-docs
description: >-
  Updates design.md, roadmap.md, and ImplementationHistory.md with the work done
  in this session so far. Use when the user invokes /update_docs or asks to sync
  session work into project docs.
disable-model-invocation: true
---

# update_docs

## Instructions

When invoked, update these three files with the work done in **this session** so far:

- **`design.md`** (repo root) — MVP contract: align §10 deployment, §13 backlog, security/S3/Lambda bullets if the session changed behavior or shipped infra.
- **`roadmap.md`** — Phase 2+ vision: adjust **MVP baseline (shipped)** or bridge table only when the session materially changed what exists vs future work.
- **`ImplementationHistory.md`** — Add a dated section (e.g. `## YYYY-MM-DD — short title`) with completed items, decisions, and links to files/workflows.

**Before editing:** Read **`AGENTS.md`** and load **`design.md`** first so updates stay consistent with the MVP contract.

**Style:** Factual bullets; link paths and workflow names; avoid duplicating full API tables unless the session changed contracts. Do not invent shipped features that are not in the repo or AWS.

## Examples

- After landing GitHub Actions workflows: add `ImplementationHistory` entry listing workflow files; extend `design.md` §10 CI/CD bullets.
- After deleting AWS resources: note in `ImplementationHistory` only; update `design.md` only if deployment assumptions change.
