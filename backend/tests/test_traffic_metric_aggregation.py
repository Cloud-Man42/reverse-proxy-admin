from datetime import datetime, timedelta

import json

import pytest

from app.models.proxy_traffic import ProxyTrafficAggregate
from app.services.metrics_service import MetricsService
from app.services.proxy_traffic_service import ProxyTrafficService, _merge_status_codes, _new_bucket


@pytest.mark.unit
def test_status_code_merge_helper():
    merged = _merge_status_codes('{"200":1}', {"404": 2, "200": 1})
    data = json.loads(merged)
    assert data["200"] == 2
    assert data["404"] == 2


@pytest.mark.unit
def test_minute_and_hour_buckets_exist(temp_settings, db_session):
    service = ProxyTrafficService(temp_settings, db_session)
    hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    minute = datetime.utcnow().replace(second=0, microsecond=0)

    minute_totals = _new_bucket()
    minute_totals["requests"] = 1
    minute_totals["bytes_in"] = 10
    minute_totals["bytes_out"] = 20
    minute_totals["status_codes"] = {"200": 1}

    hour_totals = _new_bucket()
    hour_totals["requests"] = 5
    hour_totals["bytes_in"] = 50
    hour_totals["bytes_out"] = 60
    hour_totals["status_codes"] = {"502": 1}

    service._upsert_aggregate("app-a", minute, minute_totals, period_type="minute")
    service._upsert_aggregate("app-a", hour, hour_totals, period_type="hour")
    db_session.commit()

    rows = db_session.query(ProxyTrafficAggregate).all()
    assert len(rows) == 2
    assert {row.period_type for row in rows} == {"minute", "hour"}


@pytest.mark.unit
def test_metrics_service_merges_status_codes(temp_settings, db_session):
    start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    db_session.add(
        ProxyTrafficAggregate(
            proxy_id="app-a",
            period_start=start,
            period_end=start + timedelta(minutes=1),
            period_type="minute",
            requests=2,
            status_codes_json='{"200":1,"502":1}',
        )
    )
    db_session.commit()

    merged = MetricsService(temp_settings, db_session)._merge_status_codes("1h")
    assert merged["200"] == 1
    assert merged["502"] == 1
