from pathlib import Path

from nanobot.knowledge.models import FactUpdate, IntakeDecision, LedgerRow
from nanobot.knowledge.store import KnowledgeStore


def test_knowledge_store_bootstraps_workspace(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)

    store.bootstrap()

    assert (tmp_path / "inbox").is_dir()
    assert (tmp_path / "entities").is_dir()
    assert (tmp_path / "ledgers").is_dir()
    assert (tmp_path / "indexes").is_dir()
    assert (tmp_path / "inbox" / "review").is_dir()


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
