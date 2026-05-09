---
name: execute-plan
description: >-
  Executes a written plan slice-by-slice using the Task subagent sequentially
  with model composer 2 fast, gated on passing tests and explicit per-slice
  reports before the next slice begins (avoids context rot). Expects the parent
  to keep session todos synced to plan slices. Use when the user invokes
  /execute_plan, asks to execute a plan with one subagent at a time, or wants
  phased plan execution with verification between slices.
disable-model-invocation: true
---

# /execute_plan

**Core directive (verbatim):** Execute each slice in a subagent to avoid context rot. it should use composer 2. only a single subagent at a time, wait for it to finish and run its tests and succeed in them all and reporting back with results before kicking off the next agent. go

## Role of the parent agent (this chat)

You **orchestrate** the plan. You **do not** implement full slices inline when this skill applies: you **delegate each slice** to **exactly one** Task subagent, **wait** until it finishes, **run tests** (or accept only if the subagent ran the agreed commands and you **re-run** them to confirm), require **all relevant tests to pass**, collect a **written report** for that slice, **then** start the next Task. **Never** launch two or more Task subagents at once for this workflow.

## Todo list (parent)

The session todo list is the **living map** of execution state. Keep it **continuously** aligned with reality—never let it drift behind chat or stale after a slice finishes.

1. **Start** — From the plan, create todos that cover every slice (or every verifiable step if slices are coarse). Prefer **one** todo **in progress** at a time (many **pending** is fine).
2. **Before each Task** — Set the current slice’s todo to **in progress** before launching that subagent. Prior completed slices stay **completed**.
3. **After green + slice report** — Mark the slice **completed** immediately. Ensure the **next** slice is **pending** (or becomes **in progress** only when its Task actually starts).
4. **Failures or blockers** — Do not leave an item stuck **in progress** while you fix tests or clarify scope; reflect **blocked** / follow-up splits / new todos as needed.
5. **Shutdown** — When stopping (success or deferral), reconcile todos: completed, cancelled with reason, or updated so nothing falsely claims unfinished work.

## Model and concurrency

- **Model:** Every Task invocation for plan execution **must** set `model` to **`composer-2-fast`** (Composer 2).
- **Concurrency:** **One** subagent at a time: `run_in_background` **false** (default). Do not batch parallel Tasks for plan slices under this skill.

## Per-slice workflow

Repeat for each slice in the plan (in order unless the plan explicitly allows reordering):

1. **Prepare the slice prompt** — Include: goal, file paths, constraints, acceptance criteria, and which tests to run. Point to repo conventions (`AGENTS.md`, boundaries) when the slice touches them. **Update todos** (current slice → in progress) before the next step.
2. **Launch Task** — `subagent_type`: prefer `generalPurpose` for implementation; use `explore` or `shell` only when the slice is read-only or command-only. Set `model: composer-2-fast` and **do not** set `run_in_background: true`.
3. **Wait for completion** — Read the subagent’s final message; treat missing or vague handoff as **failure to proceed** (ask one focused follow-up or re-run the slice with a tighter prompt).
4. **Run tests** — Execute the **smallest** command set that proves the slice (e.g. targeted `vitest` path, `pytest` path, `npm run lint` if the slice touched linted code). For StreamMyCourse, align with **Before merging** in `AGENTS.md` for the layers the slice changed; at minimum run what the plan and slice require.
5. **Gate** — If **any** required test or check fails: **do not** start the next subagent. Fix forward by delegating a **follow-up** Task (still one at a time) or adjust the slice until green.
6. **Report to the user** — After the slice is green, post a short **slice report**: what changed, commands run, pass/fail summary, and the next slice (if any). **Mark the slice todo completed** in the same turn.
7. **Next slice** — Only then invoke Task again for the following slice.

## Subagent prompt contract

Each Task prompt should require the subagent to:

- Stay within the **single** slice scope.
- **Run** the tests it owns before returning and list **exact commands** and **outcomes** in its summary.
- Return a **handoff**: files touched, risks, and anything the **next** slice must know (keep it brief).
- If the subagent maintains its **own** todo list for the slice, keep items accurate through completion (same discipline as the parent).

## Anti-patterns

- Spawning **multiple** Task tools for different slices in one message.
- Accepting “tests should pass” without **running** them (or without re-running when the handoff is ambiguous).
- Skipping the **per-slice user report** before starting the next subagent.
- Using a **non–Composer-2** model for slice execution under this skill.
- **Stale todos**: leaving items **in progress** after a slice is done, failing to add todos when the plan splits, or stopping without reconciling pending work.

## When this skill does not apply

- **Docs-only** or **trivial one-file** edits: inline work may be fine without Task.
- The user explicitly asks for **parallel** subagents: that contradicts this skill’s **single-subagent** rule; confirm before deviating.
