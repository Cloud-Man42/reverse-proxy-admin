from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.models.threat_feed import ThreatFeed
from app.schemas import ThreatFeedCreate, ThreatFeedType
from app.services.threat_feed_service import ThreatFeedService


def test_threat_feed_crud(temp_settings, db_session):
    service = ThreatFeedService(temp_settings, db_session)
    feed = service.create(
        ThreatFeedCreate(
            name="Test Feed",
            url="https://example.com/feed.txt",
            feed_type=ThreatFeedType.CIDR,
            enabled=True,
        )
    )
    assert feed.name == "Test Feed"
    assert service.list_feeds()
    assert service.delete(feed.id) is True


def test_fetch_ips_parses_lines(temp_settings, db_session):
    service = ThreatFeedService(temp_settings, db_session)
    feed = ThreatFeed(
        id=1,
        name="feed",
        url="https://example.com/list.txt",
        feed_type="cidr",
        enabled=True,
    )
    mock_response = MagicMock()
    mock_response.text = "# comment\n192.0.2.1\n\n203.0.113.0/24\n"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = mock_response
        client_cls.return_value = client
        ips = service._fetch_ips(feed)

    assert ips == {"192.0.2.1", "203.0.113.0/24"}


def test_sync_feed_writes_file(temp_settings, db_session, tmp_path):
    temp_settings.data_dir = tmp_path / "data"
    service = ThreatFeedService(temp_settings, db_session)
    feed_row = ThreatFeed(
        name="bad",
        url="https://example.com/bad.txt",
        feed_type="cidr",
        enabled=True,
    )
    db_session.add(feed_row)
    db_session.commit()

    mock_response = MagicMock()
    mock_response.text = "198.51.100.10\n"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = mock_response
        client_cls.return_value = client
        result = service.sync_feed(feed_row.id)

    assert result.ip_count == 1
    feed_file = temp_settings.security_dir / f"threat-feed-{feed_row.id}.conf"
    assert feed_file.exists()
    assert "deny 198.51.100.10;" in feed_file.read_text()


def test_sync_feed_http_error(temp_settings, db_session):
    service = ThreatFeedService(temp_settings, db_session)
    feed_row = ThreatFeed(
        name="fail",
        url="https://example.com/missing.txt",
        feed_type="cidr",
        enabled=True,
    )
    db_session.add(feed_row)
    db_session.commit()

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.side_effect = httpx.TimeoutException("timeout")
        client_cls.return_value = client
        with pytest.raises(httpx.TimeoutException):
            service.sync_feed(feed_row.id)

    db_session.refresh(feed_row)
    assert feed_row.last_error is not None
