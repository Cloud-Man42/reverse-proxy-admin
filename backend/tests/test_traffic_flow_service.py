from unittest.mock import patch

from app.schemas import ProxyAppCreate, ProxyRoute, TargetProtocol
from app.services.traffic_flow_service import TrafficFlowService


def test_ssl_readiness_fails_without_certificate(temp_settings):
    app = ProxyAppCreate(
        name="secure",
        domains=["secure.example.com"],
        force_https=True,
        routes=[
            ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=8080),
        ],
    )
    with patch(
        "app.services.traffic_flow_service.certificate_exists_message",
        return_value=(False, "No certificate for secure.example.com"),
    ):
        result = TrafficFlowService(temp_settings).test_ssl_readiness(app)
    assert result.success is False
    assert result.name == "ssl_readiness"


def test_ssl_readiness_passes_when_certificate_exists(temp_settings):
    app = ProxyAppCreate(
        name="secure",
        domains=["secure.example.com"],
        force_https=True,
        routes=[
            ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=8080),
        ],
    )
    with patch(
        "app.services.traffic_flow_service.certificate_exists_message",
        return_value=(True, "Certificate found for secure.example.com"),
    ):
        result = TrafficFlowService(temp_settings).test_ssl_readiness(app)
    assert result.success is True


def test_syntax_test_keeps_live_cert_paths_when_certificate_exists(temp_settings):
    app = ProxyAppCreate(
        name="secure",
        domains=["secure.example.com"],
        force_https=True,
        routes=[
            ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=8080),
        ],
    )
    service = TrafficFlowService(temp_settings)
    rendered = service.writer.render_config(app)
    test_dir = temp_settings.data_dir / "syntax-test"
    test_dir.mkdir(parents=True, exist_ok=True)
    with patch("app.services.traffic_flow_service.certificate_exists", return_value=True):
        prepared = service._prepare_rendered_for_syntax_test(rendered, test_dir, app)
    assert "/etc/letsencrypt/live/secure.example.com/fullchain.pem" in prepared
    assert "syntax-test.crt" not in prepared


def test_upstream_routes_reports_unreachable(temp_settings):
    app = ProxyAppCreate(
        name="demo",
        domains=["demo.example.com"],
        routes=[
            ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="127.0.0.1", target_port=1),
        ],
    )
    result = TrafficFlowService(temp_settings).test_upstream_routes(app)
    assert result.success is False
    assert "Cannot reach upstream" in result.message
