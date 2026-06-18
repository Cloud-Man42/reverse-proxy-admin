from app.services.access_log_parser import entry_matches_domains, parse_access_line


def test_parse_combined_access_line():
    line = (
        '198.51.100.25 - - [17/Jun/2026:13:08:39 +0000] "GET /api/proxies HTTP/1.1" '
        '200 1673 "https://10.10.20.5:8443/proxies" "Mozilla/5.0"'
    )
    parsed = parse_access_line(line)
    assert parsed is not None
    assert parsed.client_ip == "198.51.100.25"
    assert parsed.method == "GET"
    assert parsed.path == "/api/proxies"
    assert parsed.status == 200
    assert parsed.bytes_sent == 1673


def test_parse_proxy_debug_line():
    line = (
        "203.0.113.10|17/Jun/2026:13:08:39 +0000|portal.example.com|"
        "GET /login HTTP/1.1|200|512|203.0.113.99|curl/8.0"
    )
    parsed = parse_access_line(line)
    assert parsed is not None
    assert parsed.client_ip == "203.0.113.10"
    assert parsed.host == "portal.example.com"
    assert parsed.method == "GET"
    assert parsed.path == "/login"
    assert parsed.forwarded_for == "203.0.113.99"


def test_entry_matches_domains_by_host():
    parsed = parse_access_line(
        "203.0.113.10|17/Jun/2026:13:08:39 +0000|portal.example.com|GET / HTTP/1.1|200|100|-|curl/8.0"
    )
    assert parsed is not None
    assert entry_matches_domains(parsed, ["portal.example.com"])
    assert not entry_matches_domains(parsed, ["calendar.example.com"])
