import pytest
from pydantic import ValidationError

from app.schemas import ProxyAppCreate, ProxyRoute, TargetProtocol


def test_proxy_create_from_legacy_target_fields():
    app = ProxyAppCreate(
        name="myapp",
        domains=["example.com"],
        target_protocol=TargetProtocol.HTTP,
        target_host="10.0.0.10",
        target_port=8080,
    )
    assert len(app.routes) == 1
    assert app.routes[0].path_prefix == "/"
    assert app.target_host == "10.0.0.10"


def test_proxy_create_with_multiple_routes():
    app = ProxyAppCreate(
        name="multi",
        domains=["example.com"],
        routes=[
            ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=3000),
            ProxyRoute(path_prefix="/api", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=5000),
        ],
    )
    assert len(app.routes) == 2


def test_duplicate_path_prefix_rejected():
    with pytest.raises(ValidationError):
        ProxyAppCreate(
            name="dup",
            domains=["example.com"],
            routes=[
                ProxyRoute(path_prefix="/api", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=3000),
                ProxyRoute(path_prefix="/api", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=4000),
            ],
        )


def test_invalid_slug_rejected():
    with pytest.raises(ValidationError):
        ProxyAppCreate(
            name="Bad Name",
            domains=["example.com"],
            routes=[
                ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=8080),
            ],
        )


def test_invalid_domain_rejected():
    with pytest.raises(ValidationError):
        ProxyAppCreate(
            name="myapp",
            domains=["not a domain"],
            routes=[
                ProxyRoute(path_prefix="/", target_protocol=TargetProtocol.HTTP, target_host="10.0.0.1", target_port=8080),
            ],
        )


def test_empty_routes_rejected():
    with pytest.raises(ValidationError):
        ProxyAppCreate(name="myapp", domains=["example.com"], routes=[])
