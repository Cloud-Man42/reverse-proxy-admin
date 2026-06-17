import subprocess
from pathlib import Path

from app.config import Settings
from app.services.path_guard import ensure_path_allowed


class NginxOps:
    NGINX_BIN = "/usr/sbin/nginx"
    SYSTEMCTL_BIN = "/bin/systemctl"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _cmd(self, *args: str) -> list[str]:
        if self.settings.use_sudo:
            return ["sudo", *args]
        return list(args)

    def test_config(self) -> tuple[bool, str]:
        result = subprocess.run(
            self._cmd(self.NGINX_BIN, "-t"),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def reload(self) -> tuple[bool, str]:
        ok, output = self.test_config()
        if not ok:
            return False, output
        result = subprocess.run(
            self._cmd(self.SYSTEMCTL_BIN, "reload", "nginx"),
            capture_output=True,
            text=True,
            check=False,
        )
        reload_output = (result.stdout or "") + (result.stderr or "")
        combined = f"{output}\n{reload_output}".strip()
        return result.returncode == 0, combined

    def is_active(self) -> bool:
        result = subprocess.run(
            self._cmd(self.SYSTEMCTL_BIN, "is-active", "nginx"),
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "active"

    def status(self) -> tuple[bool, str]:
        active = self.is_active()
        result = subprocess.run(
            self._cmd(self.SYSTEMCTL_BIN, "status", "nginx", "--no-pager"),
            capture_output=True,
            text=True,
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
        if not output.strip() and active:
            output = "nginx is active"
        return active, output.strip()

    def enable_site(self, config_name: str) -> None:
        source = self.settings.nginx_sites_available / config_name
        target = self.settings.nginx_sites_enabled / config_name
        ensure_path_allowed(source, self.settings.allowed_read_paths())
        ensure_path_allowed(target, self.settings.allowed_write_paths(), for_write=True)
        if target.exists() or target.is_symlink():
            return
        target.symlink_to(source)

    def disable_site(self, config_name: str) -> None:
        target = self.settings.nginx_sites_enabled / config_name
        ensure_path_allowed(target, self.settings.allowed_write_paths(), for_write=True)
        if target.is_symlink() or target.exists():
            target.unlink()

    def is_enabled(self, config_name: str) -> bool:
        target = self.settings.nginx_sites_enabled / config_name
        return target.is_symlink() or target.exists()
