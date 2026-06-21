from datetime import datetime, timedelta

import pytest

from app.models.metrics import MetricAlertRule, RequestEvent
from app.models.proxy_traffic import ProxyTrafficAggregate
from app.services.alert_rule_service import AlertRuleService
from app.services.metrics_collector_service import MetricsRetentionService


@pytest.mark.unit
def test_alert_rule_error_rate_evaluation(temp_settings, db_session):
    start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    db_session.add(
        ProxyTrafficAggregate(
            proxy_id="app-a",
            period_start=start,
            period_end=start + timedelta(minutes=1),
            period_type="minute",
            requests=100,
            status_4xx=10,
            status_5xx=5,
        )
    )
    db_session.add(
        MetricAlertRule(
            name="High error rate",
            enabled=True,
            severity="warning",
            metric_type="error_rate",
            condition="gt",
            threshold=0.1,
            window_minutes=60,
            notify_email=False,
        )
    )
    db_session.commit()

    fired = AlertRuleService(temp_settings, db_session).evaluate_all()
    assert fired == 1


@pytest.mark.unit
def test_metrics_retention_purges_old_events(temp_settings, db_session):
    old = datetime.utcnow() - timedelta(days=10)
    db_session.add(
        RequestEvent(
            timestamp=old,
            proxy_id="app-a",
            client_ip="203.0.113.10",
            host="example.com",
            method="GET",
            uri="/",
            status=500,
            bytes_sent=100,
            is_failed=True,
        )
    )
    db_session.commit()

    deleted = MetricsRetentionService(db_session).cleanup()
    assert deleted["request_events"] >= 1
    assert db_session.query(RequestEvent).count() == 0
