import json

from app.services.access_log_parser import parse_access_line


def test_parse_proxy_json_line():
    line = json.dumps(
        {
            "time": "2026-06-17T13:08:39+00:00",
            "remote_addr": "203.0.113.10",
            "host": "portal.example.com",
            "request_method": "GET",
            "request_uri": "/api/health",
            "status": 200,
            "body_bytes_sent": 512,
            "request_time": 0.125,
            "upstream_response_time": "0.050",
            "upstream_addr": "10.0.0.10:8080",
            "http_user_agent": "curl/8.0",
        }
    )
    parsed = parse_access_line(line)
    assert parsed is not None
    assert parsed.host == "portal.example.com"
    assert parsed.status == 200
    assert parsed.upstream_addr == "10.0.0.10:8080"
    assert parsed.request_time == 0.125
