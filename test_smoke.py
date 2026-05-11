from agent_governance import (
    AgentGovernanceClient,
    AgentGovernanceResponse,
    AgentWrapper,
    ValidationResult,
)
from cerone import CeroneClient
from cerone import ValidationError
from cerone.cli import main as cli_main


def test_cache_key_includes_parameters():
    client = AgentGovernanceClient(api_key="sk_test", enable_cache=True)
    key_a = client._cache_key("agt_1", "trade_execute", {"symbol": "BTC", "qty": 1})
    key_b = client._cache_key("agt_1", "trade_execute", {"symbol": "BTC", "qty": 2})
    assert key_a != key_b


def test_retry_policy_defaults_to_idempotent_only():
    client = AgentGovernanceClient(api_key="sk_test")
    assert client._can_retry("GET") is True
    assert client._can_retry("POST") is False


def test_validate_cache_respects_parameters():
    client = AgentGovernanceClient(api_key="sk_test", enable_cache=True)
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
    client = AgentGovernanceClient(api_key="sk_test")

    def fake_validate(agent_id, action, parameters):
        return AgentGovernanceResponse(
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


def test_parse_validation_result_supports_flagged():
    client = AgentGovernanceClient(api_key="sk_test")
    assert client._parse_validation_result("flagged") == ValidationResult.FLAGGED


def test_parse_validation_result_unknown_defaults_to_error():
    client = AgentGovernanceClient(api_key="sk_test")
    assert client._parse_validation_result("unknown_new_state") == ValidationResult.ERROR


def test_legacy_cerone_import_remains_available():
    client = CeroneClient(api_key="sk_test")
    assert isinstance(client, AgentGovernanceClient)


def test_client_bootstraps_trial_token_when_api_key_missing():
    client = CeroneClient(api_key=None)
    client._persist_trial_token = lambda token: None
    client._load_cached_trial_token = lambda: None

    calls = []

    class _Response:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

    def fake_request(method, url, timeout=None, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/trial/session"):
            return _Response(200, {"trial_token": "sk_trial_bootstrap"})
        if url.endswith("/v1/certificates"):
            return _Response(
                200,
                {
                    "certificate": {
                        "agent_id": "agt_123",
                        "purpose": "support",
                        "capabilities": ["db_read"],
                        "signature": "sig",
                        "issued_at": "2026-05-10T00:00:00Z",
                    },
                    "trust_score": 0.95,
                },
            )
        raise AssertionError(f"Unexpected URL: {url}")

    client._session.request = fake_request
    cert = client.create_agent("support", ["db_read"])

    assert cert.agent_id == "agt_123"
    assert client.api_key == "sk_trial_bootstrap"
    assert client._session.headers["X-API-Key"] == "sk_trial_bootstrap"
    assert calls[0][1].endswith("/trial/session")
    assert calls[1][1].endswith("/v1/certificates")


def test_get_audit_log_rejects_mock_like_agent_id_locally():
    client = CeroneClient(api_key="sk_test")
    try:
        client.get_audit_log("<MagicMock id='123'>")
    except ValidationError as exc:
        assert "real Cerone agent ID" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for mock-like agent_id")


def test_validate_batch_rejects_empty_payload_locally():
    client = CeroneClient(api_key="sk_test")
    try:
        client.validate_batch([])
    except ValidationError as exc:
        assert "at least one validation item" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for empty batch")


def test_cli_version_flag_prints_version(capsys):
    rc = cli_main(["--version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "1.1.8"


def test_cli_doctor_bootstraps_trial_and_reports_usage(monkeypatch, capsys):
    health_calls = {"count": 0}

    def fake_health(self):
        health_calls["count"] += 1
        return {"status": "healthy"}

    def fake_ensure(self):
        self.api_key = "sk_trial_exampletoken"

    def fake_request(self, method, endpoint, **kwargs):
        assert method == "GET"
        assert endpoint == "/usage"
        return {
            "remaining": 2400,
            "trial_stoploss_limit": 2400,
            "validations_limit": 2500,
        }

    monkeypatch.setattr(CeroneClient, "health_check", fake_health)
    monkeypatch.setattr(CeroneClient, "_ensure_api_key", fake_ensure)
    monkeypatch.setattr(CeroneClient, "_request", fake_request)

    rc = cli_main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert health_calls["count"] == 1
    assert "Hosted trial is live." in out
    assert "2400 validations included for this hosted trial." in out
    assert "Trial token issued: sk_trial_exa...oken" in out
    assert "runtime decisions: approved, flagged, rejected" in out
