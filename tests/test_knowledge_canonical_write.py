from pathlib import Path

from nanobot.config.schema import KnowledgeConfig
from nanobot.knowledge.models import FactUpdate, IntakeDecision, LedgerRow
from nanobot.knowledge.store import KnowledgeStore


def test_apply_decision_writes_canonical_outputs_into_mehr_and_archive(tmp_path: Path) -> None:
    config = KnowledgeConfig(
        canonical_root=str(tmp_path / "Mehr"),
        archive_root=str(tmp_path / "Nanobot Archive"),
    )
    store = KnowledgeStore(tmp_path / "workspace", config)
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

    canonical_paths, archive_paths = store.apply_decision(
        decision,
        artifact_path=artifact,
        capture_id="cap-123",
    )

    assert "Front tire pressure" in (tmp_path / "Mehr/personal/bike/profile.md").read_text()
    assert "Bike serviced" in (tmp_path / "Mehr/personal/bike/history.md").read_text()
    assert "180.00" in (tmp_path / "Mehr/ledgers/expenses.csv").read_text()
    assert len(canonical_paths) >= 3
    assert len(archive_paths) == 1
    assert archive_paths[0] == tmp_path / "Nanobot Archive/2026/personal-bike/cap-123/receipt.pdf"
    assert archive_paths[0].exists()
