"""Tests del módulo ``langfuse_retention.cleanup``.

Cobertura:
    - Validaciones de seguridad (retention mínimo).
    - Lógica de preservación (scores, tags, metadata).
    - Modo dry-run NO emite DELETE.
    - Modo execute SÍ emite bulk DELETE con los IDs correctos.
    - Manejo de errores HTTP (idempotencia 404, 5xx logueado).
    - Circuit breaker MAX_DELETES_PER_RUN.
    - Paginación iterativa.
    - config_from_env lee las env vars correctas.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from langfuse_retention.cleanup import (
    BULK_DELETE_BATCH_SIZE,
    MAX_DELETES_PER_RUN,
    CleanupConfig,
    _bulk_delete_traces,
    _is_preserve_candidate,
    _list_traces_older_than,
    config_from_env,
    run_cleanup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any) -> CleanupConfig:
    base = {
        "retention_days": 180,
        "base_url": "https://test.langfuse.example",
        "public_key": "pk-test",
        "secret_key": "sk-test",
        "dry_run": True,
        "project_id": None,
    }
    base.update(overrides)
    return CleanupConfig(**base)  # type: ignore[arg-type]


def _make_trace(
    trace_id: str = "trace-1",
    *,
    scores: list[Any] | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": trace_id,
        "scores": scores,
        "tags": tags,
        "metadata": metadata,
    }


def _mock_response(status_code: int = 200, json_data: Any = None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {"data": []}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}")
    return resp


# ---------------------------------------------------------------------------
# Safety / validación
# ---------------------------------------------------------------------------


def test_retention_days_below_minimum_raises() -> None:
    config = _make_config(retention_days=5)
    with pytest.raises(ValueError, match="mínimo de seguridad"):
        run_cleanup(config)


def test_retention_days_exactly_at_minimum_is_allowed() -> None:
    config = _make_config(retention_days=30)
    with patch("langfuse_retention.cleanup.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, {"data": []})
        result = run_cleanup(config)
    assert result.retention_days == 30


# ---------------------------------------------------------------------------
# Filtros de preservación
# ---------------------------------------------------------------------------


def test_is_preserve_candidate_with_scores() -> None:
    trace = _make_trace(scores=[{"name": "manual_review", "value": 0.8}])
    preserve, reason = _is_preserve_candidate(trace)
    assert preserve is True
    assert "scores" in reason


def test_is_preserve_candidate_with_preserve_tag() -> None:
    trace = _make_trace(tags=["preserve"])
    preserve, reason = _is_preserve_candidate(trace)
    assert preserve is True
    assert "preserve" in reason


def test_is_preserve_candidate_with_audit_tag() -> None:
    trace = _make_trace(tags=["audit"])
    preserve, _ = _is_preserve_candidate(trace)
    assert preserve is True


def test_is_preserve_candidate_with_reference_tag_case_insensitive() -> None:
    trace = _make_trace(tags=["REFERENCE"])
    preserve, _ = _is_preserve_candidate(trace)
    assert preserve is True


def test_is_preserve_candidate_with_metadata_preserve_flag() -> None:
    trace = _make_trace(metadata={"preserve": True})
    preserve, reason = _is_preserve_candidate(trace)
    assert preserve is True
    assert "metadata.preserve" in reason


def test_is_preserve_candidate_normal_trace_not_preserved() -> None:
    trace = _make_trace(scores=None, tags=["normal", "production"], metadata={"x": 1})
    preserve, _ = _is_preserve_candidate(trace)
    assert preserve is False


def test_is_preserve_candidate_metadata_preserve_false_not_preserved() -> None:
    trace = _make_trace(metadata={"preserve": False})
    preserve, _ = _is_preserve_candidate(trace)
    assert preserve is False


# ---------------------------------------------------------------------------
# Dry-run vs execute
# ---------------------------------------------------------------------------


def test_dry_run_does_not_call_delete_endpoint() -> None:
    config = _make_config(dry_run=True)
    traces = [_make_trace(trace_id=f"t-{i}") for i in range(3)]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        result = run_cleanup(config)

    mock_delete.assert_not_called()
    assert result.dry_run is True
    assert result.eligible_for_delete == 3
    # En dry-run "deleted" cuenta lo que SE habría borrado.
    assert result.deleted == 3


def test_execute_calls_bulk_delete_endpoint() -> None:
    config = _make_config(dry_run=False)
    traces = [_make_trace(trace_id=f"t-{i}") for i in range(3)]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        mock_delete.return_value = _mock_response(200)
        result = run_cleanup(config)

    assert mock_delete.called
    call_kwargs = mock_delete.call_args.kwargs
    assert call_kwargs["json"] == {"traceIds": ["t-0", "t-1", "t-2"]}
    assert result.deleted == 3


def test_execute_preserves_traces_with_scores() -> None:
    config = _make_config(dry_run=False)
    traces = [
        _make_trace(trace_id="t-keep", scores=[{"name": "ok", "value": 1.0}]),
        _make_trace(trace_id="t-delete"),
    ]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        mock_delete.return_value = _mock_response(200)
        result = run_cleanup(config)

    assert result.preserved == 1
    assert result.eligible_for_delete == 1
    # El IDs enviado al endpoint NO incluye al preservable.
    sent_ids = mock_delete.call_args.kwargs["json"]["traceIds"]
    assert "t-keep" not in sent_ids
    assert "t-delete" in sent_ids


# ---------------------------------------------------------------------------
# Errores HTTP
# ---------------------------------------------------------------------------


def test_delete_failure_recorded_in_errors() -> None:
    config = _make_config(dry_run=False)
    traces = [_make_trace(trace_id="t-1")]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        mock_delete.return_value = _mock_response(500, text="Internal error")
        result = run_cleanup(config)

    assert result.deleted == 0
    assert len(result.errors) == 1
    assert "500" in result.errors[0]


def test_404_treated_as_success_idempotent() -> None:
    config = _make_config(dry_run=False)
    traces = [_make_trace(trace_id="t-stale")]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        mock_delete.return_value = _mock_response(404)
        result = run_cleanup(config)

    assert result.deleted == 1
    assert result.errors == []


def test_network_error_recorded_in_errors() -> None:
    config = _make_config(dry_run=False)
    traces = [_make_trace(trace_id="t-1")]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete:
        mock_get.return_value = _mock_response(200, {"data": traces})
        mock_delete.side_effect = requests.ConnectionError("DNS resolution failed")
        result = run_cleanup(config)

    assert result.deleted == 0
    assert len(result.errors) == 1
    assert "network error" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


def test_circuit_breaker_truncates_when_above_max_deletes() -> None:
    config = _make_config(dry_run=True)
    # Producimos más traces que el cap. Forzamos una sola página grande.
    n = MAX_DELETES_PER_RUN + 5
    traces = [_make_trace(trace_id=f"t-{i}") for i in range(n)]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get:
        # First page returns ALL traces (page_size grande para evitar paginar).
        mock_get.side_effect = [
            _mock_response(200, {"data": traces}),
            _mock_response(200, {"data": []}),  # next page empty
        ]
        result = run_cleanup(config)

    assert result.inspected == n
    assert result.eligible_for_delete == n
    # Circuit breaker capó al máximo.
    assert result.deleted == MAX_DELETES_PER_RUN
    assert any("MAX_DELETES_PER_RUN" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Paginación
# ---------------------------------------------------------------------------


def test_pagination_handled_correctly() -> None:
    config = _make_config()
    page_size = 100
    page1 = [_make_trace(trace_id=f"p1-{i}") for i in range(page_size)]
    page2 = [_make_trace(trace_id=f"p2-{i}") for i in range(50)]  # menor → fin

    with patch("langfuse_retention.cleanup.requests.get") as mock_get:
        mock_get.side_effect = [
            _mock_response(200, {"data": page1}),
            _mock_response(200, {"data": page2}),
        ]
        result = run_cleanup(config)

    assert result.inspected == page_size + 50
    assert mock_get.call_count == 2


def test_pagination_stops_on_empty_page() -> None:
    config = _make_config()
    with patch("langfuse_retention.cleanup.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, {"data": []})
        result = run_cleanup(config)
    assert result.inspected == 0
    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# Bulk delete batching
# ---------------------------------------------------------------------------


def test_bulk_delete_respects_batch_size() -> None:
    config = _make_config(dry_run=False)
    n = BULK_DELETE_BATCH_SIZE * 2 + 5
    traces = [_make_trace(trace_id=f"t-{i}") for i in range(n)]

    with patch("langfuse_retention.cleanup.requests.get") as mock_get, patch(
        "langfuse_retention.cleanup.requests.delete"
    ) as mock_delete, patch("langfuse_retention.cleanup.time.sleep"):
        # Una sola página suficiente; siguiente vuelve vacía
        mock_get.side_effect = [
            _mock_response(200, {"data": traces}),
            _mock_response(200, {"data": []}),
        ]
        mock_delete.return_value = _mock_response(200)
        result = run_cleanup(config)

    # 3 batches: 100 + 100 + 5
    assert mock_delete.call_count == 3
    assert result.deleted == n


def test_bulk_delete_returns_zero_on_empty_ids() -> None:
    config = _make_config(dry_run=False)
    deleted, errors = _bulk_delete_traces(config, [])
    assert deleted == 0
    assert errors == []


# ---------------------------------------------------------------------------
# config_from_env
# ---------------------------------------------------------------------------


def test_config_from_env_reads_all_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.example")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")
    monkeypatch.setenv("LANGFUSE_RETENTION_DAYS", "90")
    monkeypatch.setenv("LANGFUSE_CLEANUP_DRY_RUN", "false")
    monkeypatch.setenv("LANGFUSE_PROJECT_ID", "proj-1")

    config = config_from_env()
    assert config.base_url == "https://test.example"
    assert config.public_key == "pk-x"
    assert config.secret_key == "sk-x"
    assert config.retention_days == 90
    assert config.dry_run is False
    assert config.project_id == "proj-1"


def test_config_from_env_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    # Borrar opcionales del environment del runner
    for var in (
        "LANGFUSE_RETENTION_DAYS",
        "LANGFUSE_CLEANUP_DRY_RUN",
        "LANGFUSE_PROJECT_ID",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://test.example")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-x")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-x")

    config = config_from_env()
    assert config.retention_days == 180
    assert config.dry_run is True
    assert config.project_id is None


# ---------------------------------------------------------------------------
# _list_traces_older_than — verifica que pasa el query correcto
# ---------------------------------------------------------------------------


def test_list_passes_to_timestamp_and_pagination_params() -> None:
    from datetime import UTC, datetime

    config = _make_config(project_id="my-proj")
    cutoff = datetime(2025, 11, 30, 0, 0, 0, tzinfo=UTC)

    with patch("langfuse_retention.cleanup.requests.get") as mock_get:
        mock_get.return_value = _mock_response(200, {"data": []})
        _list_traces_older_than(config, cutoff)

    params = mock_get.call_args.kwargs["params"]
    assert params["toTimestamp"] == cutoff.isoformat()
    assert params["page"] == 1
    assert params["limit"] == 100
    assert params["projectId"] == "my-proj"
    # Verifica auth tupla
    assert mock_get.call_args.kwargs["auth"] == ("pk-test", "sk-test")
