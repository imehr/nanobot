# Hybrid Digital Memory Ingestion MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an MVP hybrid memory ingestion backbone for `nanobot` that preserves raw artifacts, routes capture items into entity files and ledgers, keeps `MEMORY.md` as compact working memory, and exposes practical capture paths through a watched folder, a LAN web inbox, and existing chat channels.

**Architecture:** Add a new `nanobot.knowledge` package that owns capture intake, routing decisions, canonical workspace writes, and compact memory summaries. Keep normal conversation handling intact, but add an explicit capture mode that frontends can use. Reuse the existing gateway, session manager, and media handling where possible instead of inventing a parallel runtime.

**Tech Stack:** Python 3.11, Typer, `http.server`, Pydantic, asyncio, pathlib, csv/json, pytest, existing `nanobot` agent loop and channel gateway

---

### Task 1: Add config for knowledge intake and local inbox services

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/config/schema.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_config.py`

**Step 1: Write the failing test**

Add a config test covering new defaults:

```python
from nanobot.config.schema import Config


def test_knowledge_config_defaults() -> None:
    config = Config.model_validate({})
    assert config.knowledge.enabled is True
    assert config.knowledge.inbox_dir == "inbox"
    assert config.knowledge.entities_dir == "entities"
    assert config.knowledge.ledgers_dir == "ledgers"
    assert config.knowledge.indexes_dir == "indexes"
    assert config.knowledge.review_dir == "inbox/review"
    assert config.knowledge.local_web.enabled is True
    assert config.knowledge.local_web.bind == "127.0.0.1"
    assert config.knowledge.local_web.port == 18791
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_config.py::test_knowledge_config_defaults -v
```

Expected: FAIL because `Config` does not yet expose `knowledge`.

**Step 3: Write minimal implementation**

Add config models near the other top-level config sections:

```python
class LocalWebInboxConfig(Base):
    enabled: bool = True
    bind: str = "127.0.0.1"
    port: int = 18791
    auth_token: str = ""


class KnowledgeConfig(Base):
    enabled: bool = True
    inbox_dir: str = "inbox"
    entities_dir: str = "entities"
    ledgers_dir: str = "ledgers"
    indexes_dir: str = "indexes"
    review_dir: str = "inbox/review"
    watched_paths: list[str] = Field(default_factory=list)
    local_web: LocalWebInboxConfig = Field(default_factory=LocalWebInboxConfig)


class Config(BaseSettings):
    ...
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
```

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_config.py::test_knowledge_config_defaults -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/config/schema.py tests/test_knowledge_config.py tests/test_commands.py
git commit -m "feat: add knowledge intake config"
```

### Task 2: Bootstrap workspace directories and metadata manifests

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/cli/commands.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/__init__.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/store.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_store.py`

**Step 1: Write the failing test**

Add a bootstrap test:

```python
from pathlib import Path

from nanobot.knowledge.store import KnowledgeStore


def test_knowledge_store_bootstraps_workspace(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    store.bootstrap()

    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "entities").is_dir()
    assert (tmp_path / "ledgers").is_dir()
    assert (tmp_path / "indexes").is_dir()
    assert (tmp_path / "inbox" / "review").is_dir()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_store.py::test_knowledge_store_bootstraps_workspace -v
```

Expected: FAIL because `KnowledgeStore` does not exist.

**Step 3: Write minimal implementation**

Create `KnowledgeStore` with:

- path helpers derived from workspace + config,
- `bootstrap()` to create all required directories,
- `save_inbox_item(...)` to allocate an item directory,
- small metadata manifest support such as `item.json`.

Update onboarding or startup code in `nanobot/cli/commands.py` so the workspace is bootstrapped when the agent is initialized.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_store.py::test_knowledge_store_bootstraps_workspace -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/cli/commands.py nanobot/knowledge/__init__.py nanobot/knowledge/store.py tests/test_knowledge_store.py
git commit -m "feat: bootstrap knowledge workspace"
```

### Task 3: Add typed intake decisions and canonical write helpers

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/models.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/store.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_store.py`

**Step 1: Write the failing tests**

Add tests for writing entity files and ledgers from a routing decision:

```python
from pathlib import Path

from nanobot.knowledge.models import FactUpdate, IntakeDecision, LedgerRow
from nanobot.knowledge.store import KnowledgeStore


def test_apply_decision_writes_profile_history_artifact_and_ledger(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    store.bootstrap()
    artifact = tmp_path / "receipt.pdf"
    artifact.write_text("stub", encoding="utf-8")

    decision = IntakeDecision(
        entities=["personal/bike"],
        facts=[FactUpdate(section="Specs", key="Front tire pressure", value="35 psi")],
        history_entries=["[2026-03-10] Bike serviced at City Motorcycles"],
        ledger_rows=[
            LedgerRow(
                ledger="expenses",
                row={"date": "2026-03-10", "entity": "personal/bike", "amount": "180.00"},
            )
        ],
        keep_original=True,
    )

    store.apply_decision(decision, artifact_path=artifact)

    assert "Front tire pressure" in (tmp_path / "entities/personal/bike/profile.md").read_text()
    assert "Bike serviced" in (tmp_path / "entities/personal/bike/history.md").read_text()
    assert list((tmp_path / "entities/personal/bike/artifacts").iterdir())
    assert "180.00" in (tmp_path / "ledgers/expenses.csv").read_text()
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_knowledge_store.py::test_apply_decision_writes_profile_history_artifact_and_ledger -v
```

Expected: FAIL because the typed models and writer methods do not yet exist.

**Step 3: Write minimal implementation**

Create lightweight Pydantic models for:

- `InboxItem`
- `FactUpdate`
- `LedgerRow`
- `FollowUpRequest`
- `IntakeDecision`

Implement `KnowledgeStore.apply_decision(...)` with deterministic file writes:

- entity profile creation/update,
- entity history append,
- artifact copy into entity `artifacts/`,
- CSV ledger append with header creation.

Keep the markdown format simple and append-safe for the MVP.

**Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_knowledge_store.py::test_apply_decision_writes_profile_history_artifact_and_ledger -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/models.py nanobot/knowledge/store.py tests/test_knowledge_store.py
git commit -m "feat: write canonical knowledge outputs"
```

### Task 4: Add the AI routing engine with explicit follow-up support

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/router.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/models.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_router.py`

**Step 1: Write the failing tests**

Add a fake-provider test that proves the router normalizes model output into an `IntakeDecision`:

```python
import pytest

from nanobot.knowledge.models import InboxItem
from nanobot.knowledge.router import KnowledgeRouter


class FakeProvider:
    async def chat(self, messages, tools=None, model=None, max_tokens=4096, temperature=0.0):
        class Response:
            has_tool_calls = True
            content = None
            tool_calls = [
                type(
                    "Call",
                    (),
                    {
                        "id": "call-1",
                        "name": "save_intake_decision",
                        "arguments": {
                            "entities": ["personal/bike"],
                            "material_type": "transaction",
                            "persistence_mode": "store_all",
                            "facts": [{"section": "Specs", "key": "Front tire pressure", "value": "35 psi"}],
                            "history_entries": ["[2026-03-10] Bike serviced"],
                            "ledger_rows": [{"ledger": "expenses", "row": {"amount": "180.00"}}],
                            "follow_up": None,
                        },
                    },
                )()
            ]
        return Response()


@pytest.mark.asyncio
async def test_router_returns_structured_decision() -> None:
    router = KnowledgeRouter(provider=FakeProvider(), model="test-model")
    item = InboxItem(content_text="Bike service receipt", user_hint="bike")
    decision = await router.route(item, current_memory="Known bike facts")
    assert decision.entities == ["personal/bike"]
    assert decision.material_type == "transaction"
    assert decision.ledger_rows[0].ledger == "expenses"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_router.py::test_router_returns_structured_decision -v
```

Expected: FAIL because `KnowledgeRouter` does not exist.

**Step 3: Write minimal implementation**

Create `KnowledgeRouter` that:

- accepts an `InboxItem`,
- builds a focused routing prompt using compact memory context,
- defines a single tool schema such as `save_intake_decision`,
- requires the model to emit a structured decision,
- parses that tool call into an `IntakeDecision`,
- falls back to `quarantine` if the provider does not return a valid decision.

Keep prompt scope narrow: classification, routing, and follow-up need only. Do not ask the router to write markdown directly.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_router.py::test_router_returns_structured_decision -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/router.py nanobot/knowledge/models.py tests/test_knowledge_router.py
git commit -m "feat: add knowledge routing engine"
```

### Task 5: Add a capture service that stores first, routes second, and asks follow-up only when required

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/service.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/store.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_router.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_service.py`

**Step 1: Write the failing test**

Add a service-level test:

```python
import pytest

from nanobot.knowledge.models import FollowUpRequest, InboxItem, IntakeDecision
from nanobot.knowledge.service import KnowledgeIntakeService


class FakeRouter:
    async def route(self, item, current_memory):
        return IntakeDecision(
            entities=["personal/bike"],
            material_type="transaction",
            persistence_mode="store_all",
            follow_up=FollowUpRequest(question="Is this personal or business?"),
        )


@pytest.mark.asyncio
async def test_capture_service_saves_item_before_follow_up(tmp_path) -> None:
    service = KnowledgeIntakeService.for_testing(tmp_path, router=FakeRouter())
    result = await service.capture_text("Bike service receipt", user_hint="bike")
    assert result.follow_up.question == "Is this personal or business?"
    assert result.inbox_item_path.exists()
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_service.py::test_capture_service_saves_item_before_follow_up -v
```

Expected: FAIL because `KnowledgeIntakeService` does not exist.

**Step 3: Write minimal implementation**

Create a service that:

- stores the raw item in the inbox first,
- calls the router,
- applies canonical writes when confidence is sufficient,
- moves low-confidence items to review,
- returns either a confirmation summary or a single follow-up question.

The service result should include:

- inbox item path,
- matched entities,
- actions taken,
- optional follow-up.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_service.py::test_capture_service_saves_item_before_follow_up -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/service.py nanobot/knowledge/store.py tests/test_knowledge_router.py tests/test_knowledge_service.py
git commit -m "feat: add knowledge intake service"
```

### Task 6: Keep `MEMORY.md` compact by generating a knowledge summary from canonical data

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/memory.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/context.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/store.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_memory_context.py`

**Step 1: Write the failing test**

Add a context test:

```python
from pathlib import Path

from nanobot.agent.memory import MemoryStore
from nanobot.knowledge.store import KnowledgeStore


def test_memory_context_includes_compact_knowledge_summary(tmp_path: Path) -> None:
    ks = KnowledgeStore(tmp_path)
    ks.bootstrap()
    (tmp_path / "entities/personal/bike/profile.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "entities/personal/bike/profile.md").write_text("# Bike\n\n- Front tire pressure: 35 psi\n", encoding="utf-8")

    memory = MemoryStore(tmp_path)
    context = memory.get_memory_context()
    assert "Front tire pressure" in context
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_memory_context.py::test_memory_context_includes_compact_knowledge_summary -v
```

Expected: FAIL because current memory context only reads `memory/MEMORY.md`.

**Step 3: Write minimal implementation**

Add a small summary builder that:

- scans canonical entity files for compact top facts,
- writes or synthesizes a short knowledge summary,
- keeps `MEMORY.md` prompt-sized,
- avoids dumping full ledgers or artifact OCR into prompt context.

`ContextBuilder` should keep loading `MemoryStore.get_memory_context()` as before; the change should stay localized in memory support code.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_memory_context.py::test_memory_context_includes_compact_knowledge_summary -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/memory.py nanobot/agent/context.py nanobot/knowledge/store.py tests/test_memory_context.py
git commit -m "feat: summarize canonical knowledge into memory context"
```

### Task 7: Add a watched-folder capture path for local Mac workflows

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/watcher.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/cli/commands.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_watcher.py`

**Step 1: Write the failing test**

Add a polling-friendly watcher test:

```python
from pathlib import Path

from nanobot.knowledge.watcher import discover_new_files


def test_discover_new_files_skips_seen_entries(tmp_path: Path) -> None:
    watched = tmp_path / "watched"
    watched.mkdir()
    item = watched / "receipt.txt"
    item.write_text("bike receipt", encoding="utf-8")

    first = discover_new_files([watched], seen=set())
    second = discover_new_files([watched], seen={str(item.resolve())})

    assert str(item.resolve()) in first
    assert second == []
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_watcher.py::test_discover_new_files_skips_seen_entries -v
```

Expected: FAIL because the watcher module does not exist.

**Step 3: Write minimal implementation**

Implement a simple polling watcher for the MVP:

- scan configured watched paths,
- skip files already seen,
- ignore temporary files and directories,
- hand new files to `KnowledgeIntakeService`.

Wire startup in `nanobot gateway` so the watcher runs as a background task when watched paths are configured.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_watcher.py::test_discover_new_files_skips_seen_entries -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/watcher.py nanobot/cli/commands.py tests/test_commands.py tests/test_knowledge_watcher.py
git commit -m "feat: add watched-folder knowledge capture"
```

### Task 8: Add a LAN web inbox for drag-drop, paste, and text capture

**Files:**
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/knowledge/web_inbox.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/cli/commands.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_knowledge_web_inbox.py`

**Step 1: Write the failing test**

Add a handler test for plain text capture:

```python
import json
from pathlib import Path

from nanobot.knowledge.web_inbox import build_capture_response


def test_build_capture_response_includes_follow_up() -> None:
    payload = build_capture_response(
        inbox_item_path=Path("/tmp/item"),
        entities=["personal/bike"],
        actions=["saved original", "updated bike history"],
        follow_up="Is this personal or business?",
    )
    body = json.loads(payload)
    assert body["entities"] == ["personal/bike"]
    assert body["follow_up"] == "Is this personal or business?"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_knowledge_web_inbox.py::test_build_capture_response_includes_follow_up -v
```

Expected: FAIL because the web inbox module does not exist.

**Step 3: Write minimal implementation**

Create a small `ThreadingHTTPServer`-based inbox server that:

- accepts `POST` requests for text and file uploads,
- passes them to `KnowledgeIntakeService`,
- returns JSON with saved location, matched entities, actions taken, and optional follow-up,
- binds to `127.0.0.1` by default for safety,
- optionally checks a bearer token when configured.

Start this server from `nanobot gateway` alongside existing services.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_knowledge_web_inbox.py::test_build_capture_response_includes_follow_up -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/knowledge/web_inbox.py nanobot/cli/commands.py tests/test_knowledge_web_inbox.py
git commit -m "feat: add local web inbox for knowledge capture"
```

### Task 9: Reuse chat channels for explicit remote capture

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/agent/loop.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/nanobot/channels/base.py`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_commands.py`
- Create: `/Users/mehranmozaffari/Documents/github/nanobot/tests/test_capture_mode.py`

**Step 1: Write the failing test**

Add a direct-agent test that capture metadata bypasses normal chat reply generation:

```python
import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus


class DummyProvider:
    def get_default_model(self):
        return "test-model"


@pytest.mark.asyncio
async def test_capture_mode_routes_to_knowledge_service(tmp_path) -> None:
    loop = AgentLoop(bus=MessageBus(), provider=DummyProvider(), workspace=tmp_path)
    msg = InboundMessage(
        channel="telegram",
        sender_id="1",
        chat_id="1",
        content="Bike receipt",
        metadata={"capture_mode": True, "user_hint": "bike"},
    )
    response = await loop._process_message(msg)
    assert response is not None
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_capture_mode.py::test_capture_mode_routes_to_knowledge_service -v
```

Expected: FAIL because capture mode is not wired into the agent loop.

**Step 3: Write minimal implementation**

Add a narrow explicit-capture path:

- if inbound metadata includes `capture_mode`,
- send the item to `KnowledgeIntakeService`,
- return a short acknowledgement or follow-up question,
- keep ordinary chat on the existing agent path.

Do not try to infer capture mode from every normal message in the MVP.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_capture_mode.py::test_capture_mode_routes_to_knowledge_service -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add nanobot/agent/loop.py nanobot/channels/base.py tests/test_capture_mode.py tests/test_commands.py
git commit -m "feat: support explicit capture mode for chat channels"
```

### Task 10: Document the user workflows and rollout boundaries

**Files:**
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/README.md`
- Modify: `/Users/mehranmozaffari/Documents/github/nanobot/workspace/AGENTS.md`

**Step 1: Write the failing doc checklist**

Capture the expected docs changes in the commit message or task notes:

- explain the hybrid storage layout,
- explain watched-folder and local web inbox setup,
- explain explicit capture mode for Telegram/WhatsApp,
- explain what stays out of scope for the MVP.

**Step 2: Review current docs**

Run:

```bash
rg -n "memory|Telegram|WhatsApp|gateway" README.md workspace/AGENTS.md
```

Expected: existing docs mention channels and `MEMORY.md`, but not hybrid knowledge capture.

**Step 3: Write minimal implementation**

Update docs to show:

- how to enable the local web inbox,
- how to configure watched paths,
- where artifacts, entities, and ledgers are stored,
- how capture-mode messages differ from normal chat.

**Step 4: Verify docs are coherent**

Run:

```bash
sed -n '1,260p' README.md
sed -n '1,220p' workspace/AGENTS.md
```

Expected: the new docs are consistent with the implemented flow.

**Step 5: Commit**

```bash
git add README.md workspace/AGENTS.md
git commit -m "docs: add hybrid memory ingestion workflows"
```

Plan complete and saved to `docs/plans/2026-03-10-hybrid-digital-memory-ingestion-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
