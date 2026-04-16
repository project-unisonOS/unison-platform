# Milestone 2 Intent Orchestration Brief

## Purpose

Milestone 2 should move UnisonOS from a supportable Milestone 1 baseline toward the actual intended product experience: an intent-centric operating surface that can interpret a person’s intent across modalities, select the right execution path, and return a coherent response without forcing the person to think in tools, apps, or procedural steps.

This brief defines the recommended Milestone 2 focus, boundaries, repo scope, and acceptance criteria.

## Why this is the right Milestone 2

The current vision and architecture documents point toward the same core requirement:

- intent is the atomic unit
- experience is generated, not navigated
- modality should not change meaning
- the orchestrator is the central router and planner
- tools, skills, connectors, actuation, and delegated agents are implementation details behind the experience

That means Milestone 2 should not be framed narrowly as “context,” “memory,” or one modality path in isolation.

Instead, Milestone 2 should make the intent orchestration loop meaningfully real.

## Milestone 2 goal

Make UnisonOS reliably perform a modality-independent intent orchestration loop:

1. receive input from a supported modality
2. normalize that input into intent
3. classify the nature of the requested outcome
4. choose the right execution path
5. use context where relevant
6. enforce policy and consent where needed
7. return a coherent response through the available experience surface

## Target experience outcome

A person interacting with UnisonOS should increasingly feel that:

- the system understands what they are trying to accomplish
- the system does not require them to think in apps, files, or tools
- the same intent works coherently across modalities
- the system chooses the right kind of response or action path behind the scenes
- continuity and context improve the outcome without making the experience feel invasive or unpredictable

## Recommended primary repository

Primary repo:
- `unison-orchestrator`

Why:
- this is the clearest system center for intent classification, routing, planner behavior, and execution-path selection

## Likely supporting repositories

Include only as needed:

- `unison-context`
  - for continuity, user state, and context retrieval relevant to routing
- `unison-intent-graph`
  - for normalized intent handling, routing metadata, or orchestration-adjacent state
- `unison-experience-renderer`
  - for ensuring the surfaced response remains coherent with orchestration decisions
- `unison-io-speech` and other I/O repos
  - only at the normalization/integration boundary where modality input enters the orchestration path
- `unison-platform`
  - only if runtime wiring, validation, or deployment support is needed for the Milestone 2 path

## Recommended scope for Milestone 2

Milestone 2 should focus on the system’s ability to choose among several execution paths, not just generate text.

The orchestration layer should become capable of deciding between at least these path types:

- direct informational response
- context retrieval or recall
- tool/capability invocation
- skill/procedure execution
- delegated agent flow
- actuation or VDI-backed path when an external system must be manipulated

The person should not need to understand which path was selected unless transparency is needed for safety, consent, or debugging.

## Non-goals

Milestone 2 should not try to solve all of the following at once:

- full multimodal perfection across every modality repo
- complete world-modeling or long-horizon memory systems
- broad release pipeline redesign
- large UI or renderer redesign unrelated to intent orchestration
- full agent marketplace or large-scale connector ecosystem
- reopening the Milestone 1 native install contract unless strictly necessary

## Milestone 1 carried-forward items

These remain open but should not block Milestone 2 start:

- real native install validation pass on target hardware is still pending
- full GitHub Actions proof of the revised release workflow is still pending
- the native runtime profile is explicit but still relatively broad in service shape
- some docs information architecture work remains optional cleanup, not a milestone gate

## Milestone 2 acceptance criteria

Milestone 2 should be considered successful only if it proves real intent-centric orchestration behavior.

Recommended acceptance criteria:

### 1. Intent normalization
- At least two modalities can express the same underlying request and reach the same orchestration semantics.

### 2. Execution-path selection
- The orchestrator can distinguish among at least:
  - direct response
  - context-backed response
  - tool/capability invocation
  - skill or procedural flow
  - delegated agent flow
  - actuation/VDI path

### 3. Context-aware routing
- Relevant context can improve routing or outcome quality without requiring repeated restatement from the person.

### 4. Coherent surfaced response
- The renderer or equivalent response layer presents a coherent outcome consistent with the chosen execution path.

### 5. Safety and consent boundaries
- High-impact actions continue to pass through policy and consent checks before execution.

### 6. Observability and debugging
- Developers can determine why a given orchestration path was chosen and reproduce the decision flow with enough determinism to debug behavior.

## Suggested first implementation packet

The first Milestone 2 implementation packet should likely answer these questions concretely:

- What is the canonical intent envelope entering the orchestrator?
- Where does modality normalization end and orchestration begin?
- What routing taxonomy should the orchestrator use to distinguish response/tool/skill/agent/actuation paths?
- What minimum context signals are allowed to affect routing?
- How should orchestration decisions be surfaced for debugging without leaking internals into the person-facing experience?

## Recommended first validation scenario

Use one scenario that can be expressed in multiple ways and that forces a routing decision.

For example:
- ask for a contextual summary or briefing
- ask for a direct factual answer
- ask for a task that requires a tool or delegated capability

This should demonstrate that UnisonOS is not merely generating text, but selecting execution behavior appropriate to the intent.

## Bottom line

Milestone 2 should make UnisonOS feel more like the system described in the vision documents:

- intent-centric
- modality-independent
- context-aware
- orchestration-driven
- calm, coherent, and trustworthy

That is the most strategic next step after stabilizing the Milestone 1 install/runtime/release baseline.
