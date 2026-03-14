# Project Memory Layer Design

## Goal

Add a lightweight project-memory layer that lets Nanobot capture the essence of engineering work across time without duplicating each repository's full technical documentation.

The system should:
- keep detailed technical truth inside each project repo
- keep concise cross-project memory in `Mehr`
- let queued captures update project memory when work is significant
- make project decisions, milestones, and feature summaries retrievable later

## Recommended Model

Use a linked hybrid model:

- **Repo** is the technical source of truth
  - design docs
  - implementation plans
  - ADRs and migration notes
  - feature-specific engineering documentation
- **Mehr** is the human/project memory layer
  - what the project is
  - why it matters
  - major decisions
  - recent milestones
  - current status
  - links back to repo docs
- **Nanobot Archive** remains the home for preserved raw artifacts when needed

This avoids two bad outcomes:
- `Mehr` becoming a second engineering wiki that drifts from the repo
- repos becoming the only place important project knowledge lives, making broader memory retrieval weak

## Storage Structure In Mehr

Add a shared project root:

- `Mehr/Projects/`

Each active project gets a folder:

- `Mehr/Projects/nanobot/`
- `Mehr/Projects/ImageToSTL/`
- future projects follow the same pattern

Each project folder should contain:

- `index.md`
  - high-level project summary
  - purpose
  - current state
  - active priorities
  - key links
- `decisions.md`
  - short architectural/product decisions
  - reason and implication
  - links to detailed repo docs if available
- `timeline.md`
  - dated milestones
  - notable capabilities, fixes, direction changes
- `features/`
  - optional short summaries for important features
- `links.md`
  - repo path, important docs, related tooling and operational links

## Content Rules

### What belongs in project memory

Write to `Mehr/Projects/...` when work is meaningful later across time or contexts:

- architectural decisions
- workflow changes
- important user-facing features
- major fixes or reliability changes
- changes in how the project fits into business/personal systems
- important links to detailed docs

### What does not belong there

Do not create project-memory entries for:

- tiny refactors
- local debugging steps
- test-only cleanup
- small doc wording changes
- temporary experimental notes

### Level of detail

Project memory should be compressed and readable.

Good format:
- one short paragraph or a few bullets per decision/milestone
- explicit date
- explicit implication
- link back to detailed repo artifacts where relevant

Bad format:
- commit-by-commit changelog
- long engineering implementation notes copied from repo docs

## Capture And Routing Integration

Project memory becomes another canonical routing target.

When a capture is about engineering work, Nanobot should decide:

1. is this primarily repo documentation?
2. is this significant enough for project memory in `Mehr`?
3. should both be updated?

Examples:

- a design doc written in a repo
  - full version stays in repo
  - short summary goes to `Mehr/Projects/<project>/decisions.md` or `timeline.md`
- a substantial new feature
  - repo keeps implementation/design details
  - `Mehr/Projects/<project>/features/<feature>.md` gets a concise summary
- a temporary debugging screenshot
  - maybe archive it if useful
  - usually no project-memory update
- a meaningful workflow change like queued capture writing to `Mehr`
  - add a decision entry
  - add a timeline milestone
  - update project `index.md` if current capabilities changed

## Queue And Worker Behavior

This should integrate with the existing queued capture model rather than bypass it.

Recommended flow:

1. capture enters the queue as normal
2. worker classifies it
3. if it is project-related, worker proposes a `project_memory` write action
4. canonical memory is written into `Mehr/Projects/<project>/...`
5. queue status records which project-memory files were updated
6. app/channel surfaces can show those destinations in final status

This keeps project memory consistent with the rest of the capture pipeline.

## Repo Linking Strategy

Each project `index.md` should include:

- repo name
- repo path
- main documentation paths
- current important decisions
- last meaningful update

Each `decisions.md` and `features/*.md` entry should support links to:

- local repo paths
- design docs in `docs/plans/`
- operational files when useful

That makes `Mehr` a retrieval hub, not a detached duplicate.

## Retrieval Behavior

When you ask a question like:

- "What did we decide about Nanobot capture?"
- "What major features did we add to Nanobot this month?"
- "Where is the detailed design doc for queued capture?"

Nanobot should search in this order:

1. `Mehr/Projects/<project>/index.md`
2. `Mehr/Projects/<project>/decisions.md`
3. `Mehr/Projects/<project>/timeline.md`
4. `Mehr/Projects/<project>/features/*.md`
5. linked repo docs if the summary points there

This keeps high-level memory fast while still preserving a bridge to detailed documentation.

## Suggested Initial Nanobot Project Memory

For `nanobot`, create:

- `Mehr/Projects/nanobot/index.md`
- `Mehr/Projects/nanobot/decisions.md`
- `Mehr/Projects/nanobot/timeline.md`
- `Mehr/Projects/nanobot/features/macos-capture.md`
- `Mehr/Projects/nanobot/features/queued-mehr-memory.md`
- `Mehr/Projects/nanobot/links.md`

The first seed content should summarize:

- hybrid capture architecture
- Mac app and Share extension work
- shift to queued capture processing
- `Mehr` as canonical memory root
- `Nanobot Archive` as preserved originals outside `Mehr`

## Operational Visibility

Project-memory writes should also appear in operational status surfaces.

Good examples:
- Capture app recent entries can show "Updated project memory: nanobot/timeline.md"
- queue logs can store linked project-memory outputs
- Telegram or other channels can say "Saved to Mehr and updated Nanobot project memory"

Operational logs themselves should stay out of `Mehr`.

## Why This Design Fits Your Use Case

You want something like a documentary memory of the work you are doing across projects, but not an indiscriminate surveillance log of every keystroke.

This design captures:
- the essence of what changed
- the decisions that matter later
- the context around why it changed
- the links back to the source material

without turning `Mehr` into a copy of your repositories.
