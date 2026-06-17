from unittest.mock import patch

import pytest

from app.services.log_reader import LogReader


@pytest.mark.api
@patch.object(LogReader, "read_error_log", return_value=["error line"])
def test_error_logs(mock_read, client, auth_session):
    response = client.get("/api/logs/error", cookies=auth_session["cookies"])
    assert response.status_code == 200
    assert response.json()["lines"] == ["error line"]
    mock_read.assert_called_once()


@pytest.mark.api
def test_access_logs_invalid_lines(client, auth_session):
    response = client.get("/api/logs/access?lines=0", cookies=auth_session["cookies"])
    assert response.status_code == 422
