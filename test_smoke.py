import warnings

from agent_governance import (
    AgentGovernanceClient,
    AgentGovernanceResponse,
    AgentWrapper,
    LocalErrorCategory,
    LocalValidationError,
    TelemetryEventType,
    ValidationResult,
    infer_agent_profile_from_action,
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
            policy_families=[],
            matched_rule_ids=[],
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


def test_infer_agent_profile_from_action_aligns_file_read_intent():
    profile = infer_agent_profile_from_action(
        "file_read",
        {"path": "README.md"},
        workspace_target="repository files such as README.md",
    )

    assert profile.inferred is True
    assert profile.capabilities == ["file_read"]
    assert "Perform file_read operations" in profile.purpose
    assert "repository files such as README.md" in profile.purpose


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
            assert kwargs["headers"]["X-Cerone-Client-Intent"] == "sdk_trial_bootstrap_called"
            return _Response(200, {"trial_token": "sk_trial_bootstrap"})
        if url.endswith("/v1/certificates"):
            assert kwargs["headers"]["X-Cerone-Client-Intent"] == "sdk_create_agent_called"
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
    except LocalValidationError as exc:
        assert "at least one validation item" in str(exc)
        assert "Use validate(...)" in str(exc)
        assert exc.category == LocalErrorCategory.EMPTY_BATCH
    else:
        raise AssertionError("Expected ValidationError for empty batch")


def test_low_level_request_rejects_empty_batch_payload_locally(monkeypatch):
    client = CeroneClient(api_key="sk_test")

    def fail_request(*args, **kwargs):
        raise AssertionError("Network call should not happen for empty batch payload")

    monkeypatch.setattr(client._session, "request", fail_request)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            client._request("POST", "/v1/validate/batch", json={"validations": []})
    except LocalValidationError as exc:
        assert "at least one validation item" in str(exc)
        assert "Use validate(...)" in str(exc)
        assert exc.category == LocalErrorCategory.EMPTY_BATCH
    else:
        raise AssertionError("Expected ValidationError for low-level empty batch request")
    finally:
        client.close()


def test_low_level_request_emits_deprecation_warning(monkeypatch):
    client = CeroneClient(api_key="sk_test")
    try:
        class _Response:
            status_code = 200
            text = '{"ok": true}'

            @staticmethod
            def json():
                return {"ok": True}

        monkeypatch.setattr(client._session, "request", lambda *args, **kwargs: _Response())

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            response = client._request("GET", "/usage")

        assert response == {"ok": True}
        assert any("_request() is a private method" in str(item.message) for item in caught)
    finally:
        client.close()


def test_cli_version_flag_prints_version(capsys):
    rc = cli_main(["--version"])
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out == "1.1.23"


def test_client_uses_cerone_branded_runtime_headers():
    client = CeroneClient(api_key="sk_test")
    try:
        assert client._session.headers["User-Agent"] == "cerone-python-sdk/1.1.19"
        assert client._session.headers["X-Cerone-SDK-Name"] == "cerone-python-sdk"
        assert client._session.headers["X-Cerone-SDK-Version"] == "1.1.19"
        assert client._session.headers["X-Cerone-Runtime"] == "python"
        assert client._session.headers["X-Cerone-Client-Session"].startswith("csn_")
    finally:
        client.close()


def test_client_emits_telemetry_events_and_correlation_headers():
    seen_events = []
    client = CeroneClient(
        api_key="sk_test_telemetry",
        integration_id="openclaw-plugin",
        client_session_id="csn_test123",
        telemetry_hook=seen_events.append,
    )
    seen_request = {}

    class _Response:
        status_code = 200
        text = '{"result": "approved", "semantic_alignment": 0.88, "trust_score": 0.99, "violations": [], "policy_families": [], "matched_rule_ids": [], "timestamp": "2026-03-02T00:00:00Z"}'

        @staticmethod
        def json():
            return {
                "result": "approved",
                "semantic_alignment": 0.88,
                "trust_score": 0.99,
                "violations": [],
                "policy_families": [],
                "matched_rule_ids": [],
                "timestamp": "2026-03-02T00:00:00Z",
            }

    def fake_request(method, url, timeout=None, **kwargs):
        seen_request["method"] = method
        seen_request["url"] = url
        seen_request["headers"] = kwargs.get("headers", {})
        return _Response()

    client._session.request = fake_request
    result = client.validate("agt_telemetry", "file_read", {"path": "README.md"})

    assert result.result == ValidationResult.APPROVED
    assert seen_request["method"] == "POST"
    assert seen_request["url"].endswith("/v1/validate")
    assert seen_request["headers"]["X-Cerone-Client-Intent"] == "sdk_validate_called"
    assert seen_request["headers"]["X-Cerone-Interaction-Mode"] == "single_validation"
    assert seen_request["headers"]["X-Cerone-Client-Session"] == "csn_test123"
    assert seen_request["headers"]["X-Cerone-Integration-Id"] == "openclaw-plugin"
    assert seen_request["headers"]["X-Cerone-Runtime"] == "python"
    assert seen_request["headers"]["X-Cerone-Auth-Session"].startswith("auth_")
    assert seen_request["headers"]["X-Cerone-Request-Sequence"] == "1"
    assert seen_events[0].event_type == TelemetryEventType.CLIENT_INITIALIZED
    assert any(event.event_type == TelemetryEventType.VALIDATION_ATTEMPTED for event in seen_events)
    assert any(event.event_type == TelemetryEventType.VALIDATION_RESULT_RECEIVED for event in seen_events)


def test_create_agent_for_action_uses_inferred_profile(monkeypatch):
    client = CeroneClient(api_key="sk_test")

    def fake_request(method, endpoint, **kwargs):
        body = kwargs["json"]
        assert method == "POST"
        assert endpoint == "/v1/certificates"
        assert body["capabilities"] == ["file_read"]
        assert "Perform file_read operations" in body["purpose"]
        return {
            "certificate": {
                "agent_id": "agt_profile",
                "purpose": body["purpose"],
                "capabilities": body["capabilities"],
                "signature": "sig",
                "issued_at": "2026-05-10T00:00:00Z",
            },
            "trust_score": 0.95,
        }

    client._request = fake_request
    certificate = client.create_agent_for_action(
        "file_read",
        {"path": "README.md"},
        workspace_target="repository files such as README.md",
        environment="development",
    )

    assert certificate.agent_id == "agt_profile"
    assert certificate.declared_capabilities == ["file_read"]
    assert "Perform file_read operations" in certificate.declared_purpose


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
    assert "# For one action, start with validate(...)." in out
    assert "client.close()" in out
    assert "# Use validate_batch([...]) only when you have two or more items." in out
    assert "runtime decisions: approved, flagged, rejected" in out


def test_cli_demo_runs_live_activation_flow(monkeypatch, capsys):
    calls = {"ensure": 0, "create": 0, "validate": 0, "usage": 0}

    def fake_ensure(self):
        calls["ensure"] += 1
        self.api_key = "sk_trial_exampletoken"

    def fake_create(self, purpose, capabilities, environment=None, metadata=None):
        calls["create"] += 1
        assert purpose == "Answer customer billing questions and look up billing records."
        assert capabilities == ["db_read", "billing_api"]
        assert environment == "development"
        return type(
            "AgentCertificate",
            (),
            {
                "agent_id": "agt_demo_123",
                "purpose": purpose,
                "capabilities": capabilities,
                "trust_score": 0.98,
                "signature": "sig",
                "created_at": "2026-05-12T00:00:00Z",
            },
        )()

    def fake_validate(self, agent_id, action, parameters):
        calls["validate"] += 1
        assert agent_id == "agt_demo_123"
        assert action == "database_query"
        assert parameters == {"customer_id": "123"}
        return type(
            "CeroneResponse",
            (),
            {
                "result": ValidationResult.APPROVED,
                "trust_score": 0.97,
                "latency_ms": 43,
            },
        )()

    def fake_request(self, method, endpoint, **kwargs):
        calls["usage"] += 1
        assert method == "GET"
        assert endpoint == "/usage"
        return {"remaining": 2399}

    monkeypatch.setattr(CeroneClient, "_ensure_api_key", fake_ensure)
    monkeypatch.setattr(CeroneClient, "create_agent", fake_create)
    monkeypatch.setattr(CeroneClient, "validate", fake_validate)
    monkeypatch.setattr(CeroneClient, "_request", fake_request)

    rc = cli_main(["demo"])
    out = capsys.readouterr().out

    assert rc == 0
    assert calls == {"ensure": 1, "create": 1, "validate": 1, "usage": 1}
    assert "Running a live validation against your trial..." in out
    assert '✓ Agent created: "Demo Agent" (customer billing support)' in out
    assert "✓ Action validated: database_query" in out
    assert "Result: approved" in out
    assert "Trust score: 0.97" in out
    assert "Latency: 43ms" in out
    assert "Your trial is working. 2399 validations remaining." in out
    assert "infer_agent_profile_from_action" in out
    assert 'result = client.validate(agent.agent_id, "file_read", {"path": "README.md"})' in out


def test_validate_adds_client_intent_header():
    client = CeroneClient(api_key="sk_test")
    seen = {}

    def fake_request(method, endpoint, **kwargs):
        seen["headers"] = kwargs.get("headers", {})
        return {
            "result": "approved",
            "semantic_alignment": 0.99,
            "trust_score": 0.99,
            "violations": [],
            "timestamp": "2026-03-02T00:00:00Z",
        }

    client._request = fake_request
    result = client.validate("agt_1", "process_payment", {"amount": 10})
    assert result.result == ValidationResult.APPROVED
    assert seen["headers"]["X-Cerone-Client-Intent"] == "sdk_validate_called"
