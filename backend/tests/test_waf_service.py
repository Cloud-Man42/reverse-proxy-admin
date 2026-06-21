from app.services.waf_service import WafService
from app.models.proxy_waf_settings import ProxyWafSettings


def test_to_response_handles_null_db_values():
    row = ProxyWafSettings(proxy_id="demo")
    row.enabled = None
    row.mode = None
    row.profile = None
    response = WafService._to_response(row)
    assert response.proxy_id == "demo"
    assert response.enabled is False
    assert response.mode == "detection"
    assert response.profile == "medium"
    assert response.exclusions == []
