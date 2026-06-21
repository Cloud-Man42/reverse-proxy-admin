from app.services.error_log_parser import (
    classify_failed_request,
    parse_error_line,
    parse_proxy_json_line,
    status_code_hint,
)


def test_parse_error_line_upstream_timeout():
    line = '2026/06/17 13:08:39 [error] 123#123: *1 upstream timed out, client: 203.0.113.10, host: "app.example.com"'
    parsed = parse_error_line(line)
    assert parsed is not None
    assert parsed.client_ip == "203.0.113.10"
    assert parsed.host == "app.example.com"
    assert "upstream timed out" in parsed.message


def test_classify_failed_request_502():
    failed, hint = classify_failed_request(502)
    assert failed is True
    assert "backend" in hint.lower()


def test_status_code_hint_504():
    assert "timeout" in status_code_hint(504).lower()


def test_parse_proxy_json_line():
    payload = parse_proxy_json_line('{"status":502,"request_uri":"/"}')
    assert payload is not None
    assert payload["status"] == 502
