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
    assert config.knowledge.native_capture.enabled is False
    assert config.knowledge.native_capture.bind == "127.0.0.1"
    assert config.knowledge.native_capture.port == 18792
    assert config.knowledge.native_capture.auth_token == ""
