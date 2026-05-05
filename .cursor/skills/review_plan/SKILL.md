---
name: review-plan
description: >-
  Reviews a written plan in the same chat (Cursor Auto), performs an objective
  security audit, checks that non-trivial plans schedule /update_docs after
  success, checks for subagent delegation to avoid context rot, revises the
  plan document with findings, and surfaces clarifying questions. Mandates
  test-driven development for implementation work: tests first, then code, with
  full TDD discipline. Use when the user invokes /review_plan, asks to audit a
  plan, wants a security pass on a plan before execution, or asks for a peer
  review of a plan file (including under .cursor/plans).
disable-model-invocation: true
---

# /review_plan

Peer-style plan review (same agent / Auto): **plan quality**, **security**, **test-driven development (mandatory for code changes)**, **subagent delegation (to avoid context rot)** in the *plan under review*, **session docs closure (`/update_docs`)** where applicable, **plan file revision**, and **clarifying questions**. Stay objective; disagree with the plan when evidence supports it.

**Execution model:** Run the full review **in this chat**, in the **same agent** the user already invoked (Cursor **Auto** / default router). **Do not** spawn a separate subagent via the Task tool for plan review: that can route to a **premium billed** child agent and is **out of scope** for this skill. If the user wants another pass, they can run `/review_plan` again.

## Test-driven development (mandatory)

Any plan that adds or changes **production code** must assume **TDD**: **write automated tests first**, then implement until tests pass, then refactor. This is not optional for implementation phases the skill touches or prescribes.

### Contract with the plan

- **Ordering:** Tasks and todos must reflect **Red → Green → Refactor** per slice of behavior (see below). If the plan lists "implement X" before "test X," **reorder** or insert explicit test-first steps when revising the plan.
- **Acceptance:** "Done" for a feature includes **tests merged** that would have failed before the change and pass after it. Plans without a test strategy for new behavior are **incomplete**.
- **Review lens:** In the general plan review, explicitly check for TDD gaps (missing tests, implementation before tests, untestable design).

### Red → Green → Refactor (every vertical slice)

1. **Red — write a failing test first**
   - Add the **smallest** test that expresses one **observable behavior** or contract (not "the whole feature" in one test).
   - Run the suite and **confirm the new test fails** for the **right reason** (assertion/message you expect). A test that passes immediately is a smell: wrong test, wrong target, or behavior already present—fix before writing production code.
2. **Green — minimal production code**
   - Write only enough code to make that test pass. Avoid speculative APIs or extra behavior not covered by the current failing test.
3. **Refactor — with all tests green**
   - Improve names, structure, duplication removal, and boundaries **only** while tests stay green. If a refactor breaks tests, revert or fix in small steps.

Repeat the cycle for the next behavior until the plan's scope is covered.

### TDD best practices (enforce in plan text and review commentary)

- **Test behavior, not implementation:** Prefer public API, module boundaries, HTTP handlers, or user-visible outcomes over testing private methods or brittle internals. Tests should survive refactors that preserve behavior.
- **One clear intent per test:** Name tests so a failure reads like documentation (`it('rejects expired tokens')`). Avoid unrelated assertions in the same test.
- **Deterministic and fast:** No flakiness from time, randomness, or shared global state without explicit control. Unit tests should be fast enough to run constantly; slow work belongs in integration/e2e with clear scope.
- **Isolate external I/O at boundaries:** Use test doubles (fakes, stubs, mocks) **at system edges** (HTTP, DB, queues, clocks), not to "mock everything." Prefer real in-memory or containerized dependencies when cost is low and fidelity is high.
- **Arrange–Act–Assert (or Given–When–Then):** Keep setup, invocation, and assertions visually obvious; extract helpers only when it improves clarity, not to hide chaos.
- **Coverage is a side effect:** Aim for meaningful scenarios and edge cases, not percentage chasing. Call out missing negative paths, authz, and error handling in the plan.
- **Test data:** Prefer builders, factories, or small fixtures over copy-pasted blobs; keep data minimal to prove the case.
- **Integration and E2E:** When the plan spans multiple services or persistence, include **where** integration tests live and **what** unit tests still own. E2E should cover critical paths sparingly; do not use E2E as a substitute for fast feedback loops.
- **Regression:** For every fixed bug, a **failing test that reproduces the bug** should land **before** the fix (same Red → Green discipline).
- **CI:** Plans should state that **tests run in CI** before merge and match local commands (same runner, env vars documented).

### When TDD is awkward (still disciplined)

- **Spikes / prototypes:** If the plan allows a throwaway spike, say so explicitly with a **time box** and **no merge** until behavior is re-derived with tests first.
- **UI-heavy work:** Prefer testing through stable selectors or component contracts; snapshot tests only where they add signal, not noise.
- **Generated code / config-only:** Skip TDD only for pure config with **other** verification (e.g. `terraform validate`, schema lint); state that in the plan.

## Subagent delegation for parallelizable tasks (avoid context rot)

Large plans with long sequential task lists cause **context rot**: the implementing agent loses coherence as the context window fills with completed work, leading to degraded decision-making, missed dependencies, and incomplete execution.

### Checklist for the plan under review

- **Parallelizable work identified:** Does the plan contain 3+ tasks that are independent (no shared state, no ordering constraints, can run concurrently)?
- **Subagent delegation specified:** Are those independent tasks marked to run via `Task` tool with `run_in_background: true` instead of sequentially inline?
- **Aggregation point defined:** Is there a clear parent-level step that awaits results and integrates findings?
- **Result contract explicit:** Does the plan specify what each subagent returns so the parent can integrate without ambiguity?
- **Context window respected:** For plans with 10+ steps, is there a strategy to parallelize or chunk work to stay within effective context limits?

### What to flag as defects

- A single todo list with 8+ sequential manual steps and no parallelization strategy
- Tasks that could run in parallel but are ordered sequentially "for simplicity"
- No explicit aggregation/join point after parallel subagents complete
- Missing result contracts ("subagents do work" without saying what they return)

### Revision guidance

When revising the plan, add:
- `## Parallel execution` section identifying which tasks can run in parallel
- Explicit `Task` tool invocations with `run_in_background: true` for parallelizable work
- A `### Aggregation` subsection specifying how the parent collects and integrates results
- Result schemas or contracts for subagent returns

## Execution pattern (single agent, no Task review subagent)

Perform the complete review **yourself** in this conversation. **Do not** use the Task tool to delegate `/review_plan` to another agent.

### Steps (you, the invoking agent)

1. **Parse the user's request**
   - Identify the plan file path (attached, explicit path, or ask once if unclear)
   - Determine the review scope (full review, security-only, or specific aspects)

2. **Run the review workflow** (below): read the plan, audit, revise the file, surface questions.

3. **Report to the user**
   - Summarize verdict, risks, TDD and delegation notes, doc closure, file edits, and clarifying questions
   - If clarifying questions remain, present them via AskQuestion when that fits better than open text

### Review workflow (execute in order)

You must execute these steps:

1. **Read the plan file** using Read tool

2. **General plan review (non-security)**
   - Goals vs steps: are outcomes and todos aligned? Missing phases (deploy, rollback, post-success `/update_docs`, tests-first for every code change)?
   - TDD: Does every implementation chunk have **failing tests specified before** implementation steps? Are Red/Green/Refactor and verification explicit? Flag untestable designs.
   - **Subagent delegation:** Are parallelizable tasks identified and marked for subagent delegation? Does the plan avoid long sequential task lists that would cause context rot? (See "Subagent delegation for parallelizable tasks" section below)
   - Assumptions and dependencies: unstated prerequisites, ordering, env coupling?
   - Contradictions: does later text undo earlier decisions?
   - Scope creep vs out-of-scope: is the boundary honest?
   - Verifiability: smoke tests, acceptance criteria, measurable done?
   - Repo fit: do cited paths and workflows match reality?

3. **Session docs closure (`/update_docs`)**
   - Read `.cursor/skills/update-docs/SKILL.md` to understand doc sync requirements
   - Check if the plan schedules `/update_docs` after success for non-trivial work
   - If missing and applicable, flag as a plan defect

4. **Security audit**
   - State clearly that no plan is "100% secure"; assess controls and residual risk
   - Cover: secrets, authn/authz, transport/redirects, data/PII, supply chain, multi-tenant isolation, threats (XSS, CSRF, IDOR), operational concerns
   - Separate "secure enough" from "must fix before merge"

5. **Revise the plan document**
   - Edit the plan file in place using StrReplace/Write tools
   - Add sections: `## Peer review`, `## Security audit`, `## Test plan (TDD)`, `## Parallel execution` (if parallelizable tasks exist), `## Documentation (post-success)` as needed
   - Insert/reorder todos so tests precede implementation
   - Restructure long sequential task lists into parallel subagent delegations where applicable
   - Add `/update_docs` final step if missing (unless docs-only/spike)

6. **Clarifying questions**
   - Derive 1-3 questions that unblock ambiguity
   - Include them in your final message to the user

**Return format (for your summary to the user):**
- Verdict (approve / revise / needs-discussion)
- Top risks found
- TDD/test-order gaps addressed
- Subagent delegation gaps addressed (parallelizable tasks identified, `Task` tool usage specified, aggregation points defined)
- Whether `/update_docs` post-success was missing and added
- Summary of file changes made
- Clarifying questions (if any)

## Instructions for the reviewer

- **Persona:** Review as if you were not the author of the plan; cite gaps and overclaims.
- **Security:** Do not checklist-wash; tie each note to a concrete asset or flow from the plan.
- **TDD:** Treat "tests after implementation" as a **plan defect** to fix in the document unless the work is explicitly out of scope for code.
- **Subagent delegation:** Treat long sequential task lists (8+ steps) without parallelization as a **plan defect**. Flag opportunities to use `Task` tool with `run_in_background: true` for independent work.
- **Revisions:** Prefer updating the single plan source of truth over only chatting findings.
- **Project context:** For StreamMyCourse non-trivial work, follow `AGENTS.md` when the plan touches product, APIs, or infra.
- **Docs after success:** Plans that ship non-trivial behavior should end with `/update_docs`.

## Output to the user (chat)

End with a concise summary covering:
- Verdict (approve / revise / needs-discussion)
- Top risks identified
- TDD / test-order gaps addressed
- Plan-level subagent delegation / context rot notes (what the *plan* should say about `Task` and parallel work—not spawning a Task agent for this review)
- Whether `/update_docs` post-success was missing and added (or rightly exempt)
- What changed in the plan file
- Clarifying questions (if any)

## Examples

- User: "`/review_plan`" with `enable_google_sign-in_*.plan.md` attached → you read the plan, run the workflow, edit the plan file (peer review, security, TDD sections, `/update_docs` if needed), then summarize in chat.
- User: "Audit this plan for security only" → same flow with emphasis on the security audit sections and summary.
