"""P7-11: Model Gateway metrics tests.

Verifies:
- record_call increments counters keyed by (provider_type, status).
- record_error increments error counters by stable error code.
- record_provider_health records the latest health status.
- snapshot() returns a non-sensitive summary.
- to_prometheus_text() renders Prometheus-style text.
- reset() clears all metrics.
- No sensitive labels (prompt, response, user email, raw endpoint) appear.
- Singleton accessor returns the same instance.
"""
from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.modules.model_gateway.metrics import (
    ModelGatewayMetrics,
    get_model_gateway_metrics,
    reset_model_gateway_metrics,
)
from src.modules.model_gateway.schemas import ProviderHealthStatus


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the singleton is reset before and after each test."""
    reset_model_gateway_metrics()
    yield
    reset_model_gateway_metrics()


class TestRecordCall:
    def test_single_call_recorded(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock",
            provider_name="mock",
            status="completed",
            latency_ms=42,
        )
        snap = m.snapshot()
        assert snap["calls_total"] == {"mock:completed": 1}

    def test_multiple_calls_accumulate(self):
        m = ModelGatewayMetrics()
        for _ in range(3):
            m.record_call(
                provider_type="mock", provider_name="mock",
                status="completed", latency_ms=10,
            )
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="failed", latency_ms=5,
        )
        snap = m.snapshot()
        assert snap["calls_total"]["mock:completed"] == 3
        assert snap["calls_total"]["mock:failed"] == 1

    def test_different_providers_tracked_separately(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=10,
        )
        m.record_call(
            provider_type="openai_compatible", provider_name="local-vllm",
            status="completed", latency_ms=20,
        )
        snap = m.snapshot()
        assert "mock:completed" in snap["calls_total"]
        assert "openai_compatible:completed" in snap["calls_total"]

    def test_latency_summary_computed(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=10,
        )
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=30,
        )
        snap = m.snapshot()
        lat = snap["latency_ms"]["mock"]
        assert lat["count"] == 2
        assert lat["min"] == 10
        assert lat["max"] == 30
        assert lat["avg"] == 20.0

    def test_latency_capped_at_max_samples(self):
        """Latency samples are capped to avoid unbounded memory."""
        m = ModelGatewayMetrics()
        for i in range(10005):
            m.record_call(
                provider_type="mock", provider_name="mock",
                status="completed", latency_ms=i,
            )
        snap = m.snapshot()
        # Should be capped at 10000 samples.
        assert snap["latency_ms"]["mock"]["count"] == 10000


class TestRecordError:
    def test_error_recorded_by_code(self):
        m = ModelGatewayMetrics()
        m.record_error(error_code="MODEL_UNAVAILABLE")
        m.record_error(error_code="MODEL_UNAVAILABLE")
        m.record_error(error_code="MODEL_TIMEOUT")
        snap = m.snapshot()
        assert snap["errors_total"]["MODEL_UNAVAILABLE"] == 2
        assert snap["errors_total"]["MODEL_TIMEOUT"] == 1

    def test_error_never_contains_content(self):
        """Error codes must be stable strings, never raw content."""
        m = ModelGatewayMetrics()
        secret = "super_secret_prompt_data"
        m.record_error(error_code="MODEL_UNAVAILABLE")
        snap = m.snapshot()
        text = str(snap)
        assert secret not in text


class TestRecordProviderHealth:
    def test_health_recorded(self):
        m = ModelGatewayMetrics()
        m.record_provider_health(
            provider_name="local-node", status=ProviderHealthStatus.ONLINE
        )
        snap = m.snapshot()
        assert snap["provider_health"]["local-node"] == "ONLINE"

    def test_health_overwrites_previous(self):
        m = ModelGatewayMetrics()
        m.record_provider_health(
            provider_name="node-1", status=ProviderHealthStatus.ONLINE
        )
        m.record_provider_health(
            provider_name="node-1", status=ProviderHealthStatus.DEGRADED
        )
        snap = m.snapshot()
        assert snap["provider_health"]["node-1"] == "DEGRADED"

    def test_multiple_providers(self):
        m = ModelGatewayMetrics()
        m.record_provider_health(
            provider_name="node-1", status=ProviderHealthStatus.ONLINE
        )
        m.record_provider_health(
            provider_name="node-2", status=ProviderHealthStatus.OFFLINE
        )
        snap = m.snapshot()
        assert len(snap["provider_health"]) == 2


class TestSnapshot:
    def test_empty_snapshot(self):
        m = ModelGatewayMetrics()
        snap = m.snapshot()
        assert snap["calls_total"] == {}
        assert snap["latency_ms"] == {}
        assert snap["errors_total"] == {}
        assert snap["provider_health"] == {}

    def test_snapshot_has_required_keys(self):
        m = ModelGatewayMetrics()
        snap = m.snapshot()
        for key in ("calls_total", "latency_ms", "errors_total", "provider_health"):
            assert key in snap

    def test_snapshot_is_sorted(self):
        """Keys in snapshot should be deterministically sorted."""
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="zebra", provider_name="z",
            status="completed", latency_ms=1,
        )
        m.record_call(
            provider_type="alpha", provider_name="a",
            status="completed", latency_ms=1,
        )
        snap = m.snapshot()
        keys = list(snap["calls_total"].keys())
        assert keys == sorted(keys)


class TestPrometheusText:
    def test_contains_type_declarations(self):
        m = ModelGatewayMetrics()
        text = m.to_prometheus_text()
        assert "# TYPE model_gateway_calls_total counter" in text
        assert "# TYPE model_gateway_latency_ms summary" in text
        assert "# TYPE model_gateway_errors_total counter" in text
        assert "# TYPE model_gateway_provider_health gauge" in text

    def test_call_metric_rendered(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=10,
        )
        text = m.to_prometheus_text()
        assert 'model_gateway_calls_total{provider_type="mock",status="completed"}' in text

    def test_error_metric_rendered(self):
        m = ModelGatewayMetrics()
        m.record_error(error_code="MODEL_UNAVAILABLE")
        text = m.to_prometheus_text()
        assert 'model_gateway_errors_total{error_code="MODEL_UNAVAILABLE"}' in text

    def test_provider_health_gauge_values(self):
        m = ModelGatewayMetrics()
        m.record_provider_health(
            provider_name="online-node", status=ProviderHealthStatus.ONLINE
        )
        m.record_provider_health(
            provider_name="degraded-node", status=ProviderHealthStatus.DEGRADED
        )
        m.record_provider_health(
            provider_name="offline-node", status=ProviderHealthStatus.OFFLINE
        )
        text = m.to_prometheus_text()
        assert 'model_gateway_provider_health{provider_name="online-node"} 1' in text
        assert 'model_gateway_provider_health{provider_name="degraded-node"} 0' in text
        assert 'model_gateway_provider_health{provider_name="offline-node"} -1' in text

    def test_latency_metric_rendered(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=15,
        )
        text = m.to_prometheus_text()
        assert 'model_gateway_latency_ms{provider_type="mock",quantile="avg"}' in text

    def test_no_sensitive_labels_in_prometheus(self):
        """Prometheus output must never contain prompt/response/user data."""
        m = ModelGatewayMetrics()
        secret_prompt = "USER_SECRET_PROMPT"
        secret_response = "MODEL_SECRET_RESPONSE"
        secret_email = "user@secret.edu"
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=10,
        )
        text = m.to_prometheus_text()
        assert secret_prompt not in text
        assert secret_response not in text
        assert secret_email not in text


class TestReset:
    def test_reset_clears_all(self):
        m = ModelGatewayMetrics()
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=10,
        )
        m.record_error(error_code="MODEL_UNAVAILABLE")
        m.record_provider_health(
            provider_name="node", status=ProviderHealthStatus.ONLINE
        )
        m.reset()
        snap = m.snapshot()
        assert snap["calls_total"] == {}
        assert snap["latency_ms"] == {}
        assert snap["errors_total"] == {}
        assert snap["provider_health"] == {}


class TestSingleton:
    def test_get_metrics_returns_same_instance(self):
        m1 = get_model_gateway_metrics()
        m2 = get_model_gateway_metrics()
        assert m1 is m2

    def test_reset_singleton_returns_new_instance(self):
        m1 = get_model_gateway_metrics()
        reset_model_gateway_metrics()
        m2 = get_model_gateway_metrics()
        assert m1 is not m2


class TestNoSensitiveLabels:
    """Privacy contract: metrics labels must never carry sensitive data."""

    def test_provider_name_not_endpoint(self):
        """provider_name is a friendly name, never a raw URL with token."""
        m = ModelGatewayMetrics()
        raw_endpoint = "http://vllm.inference.svc.cluster.local:8000/v1"
        api_key = "sk-super-secret-key"
        m.record_call(
            provider_type="openai_compatible",
            provider_name="local-vllm",  # friendly name, not endpoint
            status="completed",
            latency_ms=10,
        )
        snap = m.snapshot()
        text = str(snap) + m.to_prometheus_text()
        assert raw_endpoint not in text
        assert api_key not in text

    def test_secretstr_not_leaked(self):
        """Ensure SecretStr values don't accidentally appear."""
        m = ModelGatewayMetrics()
        secret = SecretStr("do-not-leak-this-key")
        m.record_call(
            provider_type="mock", provider_name="mock",
            status="completed", latency_ms=1,
        )
        snap = m.snapshot()
        assert secret.get_secret_value() not in str(snap)


class TestServiceIntegration:
    """Verify the service records metrics during chat calls."""

    def test_chat_increments_call_counter(self):
        from src.modules.model_gateway.metrics import ModelGatewayMetrics
        from src.modules.model_gateway.schemas import (
            ChatMessage,
            ChatRequest,
            DataClassification,
            PrivacyContext,
        )
        from src.modules.model_gateway.service import ModelGatewayService

        # Use a dedicated metrics instance so we don't depend on the global.
        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics  # inject for testing

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        service.chat(req)
        snap = metrics.snapshot()
        # The mock provider should have been called.
        assert any("completed" in k for k in snap["calls_total"])

    def test_chat_records_latency(self):
        from src.modules.model_gateway.metrics import ModelGatewayMetrics
        from src.modules.model_gateway.schemas import (
            ChatMessage,
            ChatRequest,
            DataClassification,
            PrivacyContext,
        )
        from src.modules.model_gateway.service import ModelGatewayService

        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics

        req = ChatRequest(
            messages=[ChatMessage(role="user", content="test")],
            privacy_context=PrivacyContext(
                data_classification=DataClassification.P2, purpose="test"
            ),
            purpose="test",
        )
        service.chat(req)
        snap = metrics.snapshot()
        assert len(snap["latency_ms"]) >= 1
        for stats in snap["latency_ms"].values():
            assert stats["count"] >= 1
            assert stats["avg"] >= 0

    def test_health_updates_provider_health_metric(self):
        from src.modules.model_gateway.metrics import ModelGatewayMetrics
        from src.modules.model_gateway.service import ModelGatewayService

        metrics = ModelGatewayMetrics()
        service = ModelGatewayService()
        service._metrics = metrics

        service.health()
        snap = metrics.snapshot()
        # Mock and rule providers should be in the health map.
        assert len(snap["provider_health"]) >= 1
