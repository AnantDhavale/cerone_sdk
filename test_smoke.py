from ceron_sdk import AgentWrapper, CeronClient, CeronResponse, ValidationResult


def test_cache_key_includes_parameters():
    client = CeronClient(api_key="sk_test", enable_cache=True)
    key_a = client._cache_key("agt_1", "trade_execute", {"symbol": "BTC", "qty": 1})
    key_b = client._cache_key("agt_1", "trade_execute", {"symbol": "BTC", "qty": 2})
    assert key_a != key_b


def test_retry_policy_defaults_to_idempotent_only():
    client = CeronClient(api_key="sk_test")
    assert client._can_retry("GET") is True
    assert client._can_retry("POST") is False


def test_validate_cache_respects_parameters():
    client = CeronClient(api_key="sk_test", enable_cache=True)
    calls = {"count": 0}

    def fake_request(method, endpoint, **kwargs):
        calls["count"] += 1
        return {
            "result": "approved",
            "semantic_alignment": 0.99,
            "trust_score": 0.99,
            "violations": [],
            "timestamp": "2026-03-02T00:00:00Z",
        }

    client._request = fake_request

    first = client.validate("agt_1", "process_payment", {"amount": 10})
    second = client.validate("agt_1", "process_payment", {"amount": 10})
    third = client.validate("agt_1", "process_payment", {"amount": 20})

    assert first.result == ValidationResult.APPROVED
    assert second.result == ValidationResult.APPROVED
    assert third.result == ValidationResult.APPROVED
    assert calls["count"] == 2


def test_agent_wrapper_executes_when_approved():
    client = CeronClient(api_key="sk_test")

    def fake_validate(agent_id, action, parameters):
        return CeronResponse(
            result=ValidationResult.APPROVED,
            semantic_alignment=0.95,
            trust_score=0.99,
            violations=[],
            agent_id=agent_id,
            action=action,
            timestamp="2026-03-02T00:00:00Z",
            latency_ms=1,
        )

    client.validate = fake_validate
    wrapper = AgentWrapper(client, "agt_1")

    @wrapper.validate_action
    def add_one(x):
        return x + 1

    assert add_one(2) == 3
    assert add_one.__name__ == "add_one"
