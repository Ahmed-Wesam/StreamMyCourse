---
name: start
description: Load StreamMyCourse project context by reading AGENTS.md at the repository root. Use when the user says "start" at the beginning of a new agent session to bootstrap project context before any other work.
disable-model-invocation: true
---

# /start

Bootstrap a new agent session with StreamMyCourse project context.

## Workflow

1. **Read `AGENTS.md`** at the repository root (`C:\Users\ahmad\CascadeProjects\StreamMyCourse\AGENTS.md`) using the Read tool. This file is the index for project intent and points to the rest of the relevant docs.
2. **Acknowledge briefly** that context is loaded and wait for the user's actual task. Do not preemptively read every linked doc — load `design.md`, `roadmap.md`, `ImplementationHistory.md`, `plans/architecture/`, or other linked files only when the upcoming task requires them.
3. **Do not modify files** as part of `/start`. This command is context-loading only.

## Instructions

- Read `AGENTS.md` in full (it is short).
- Keep the acknowledgement to one or two sentences (e.g. "Project context loaded from AGENTS.md. What would you like to work on?").
- Do not summarize `AGENTS.md` back to the user unless they ask.
- If `AGENTS.md` is missing, tell the user and stop.
