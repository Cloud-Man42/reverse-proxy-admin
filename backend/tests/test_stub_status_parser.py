from app.services.nginx_stub_status import parse_stub_status


SAMPLE = """
Active connections: 3
server accepts handled requests
 100 101 200
Reading: 0 Writing: 1 Waiting: 2
"""


def test_parse_stub_status():
    snapshot = parse_stub_status(SAMPLE)
    assert snapshot is not None
    assert snapshot.active == 3
    assert snapshot.reading == 0
    assert snapshot.writing == 1
    assert snapshot.waiting == 2
    assert snapshot.accepts == 100
    assert snapshot.handled == 101
    assert snapshot.requests == 200
