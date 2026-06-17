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
