from unittest.mock import MagicMock, patch

from app.config import Settings
from app.services.nginx_ops import NginxOps


def test_reload_uses_signal_when_configured():
    settings = Settings(use_sudo=False, nginx_reload_mode="signal")
    ops = NginxOps(settings)

    with patch.object(ops, "test_config", return_value=(True, "syntax ok")):
        with patch("app.services.nginx_ops.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            ok, output = ops.reload()

    assert ok is True
    assert "syntax ok" in output
    mock_run.assert_called_once_with(
        ["/usr/sbin/nginx", "-s", "reload"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_reload_uses_systemctl_by_default():
    settings = Settings(use_sudo=False, nginx_reload_mode="systemctl")
    ops = NginxOps(settings)

    with patch.object(ops, "test_config", return_value=(True, "syntax ok")):
        with patch("app.services.nginx_ops.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            ok, _output = ops.reload()

    assert ok is True
    mock_run.assert_called_once_with(
        ["/bin/systemctl", "reload", "nginx"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_is_active_signal_mode_uses_pid_file(tmp_path):
    settings = Settings(use_sudo=False, nginx_reload_mode="signal")
    ops = NginxOps(settings)
    ops.NGINX_PID_FILE = tmp_path / "nginx.pid"
    ops.NGINX_PID_FILE.write_text("1", encoding="utf-8")
    assert ops.is_active() is True
