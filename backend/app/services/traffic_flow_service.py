import shutil
import socket
import subprocess
import uuid
from pathlib import Path

from app.config import Settings
from app.schemas import ProxyAppBase, TrafficFlowCheck, TrafficFlowTestResult
from app.services.nginx_writer import NginxWriter


class TrafficFlowService:
    NGINX_BIN = "/usr/sbin/nginx"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.writer = NginxWriter(settings)

    def _cmd(self, *args: str) -> list[str]:
        if self.settings.use_sudo:
            return ["sudo", *args]
        return list(args)

    def test_upstream(self, host: str, port: int) -> TrafficFlowCheck:
        try:
            with socket.create_connection((host, port), timeout=5):
                return TrafficFlowCheck(
                    name="upstream_connectivity",
                    success=True,
                    message=f"Upstream {host}:{port} is reachable from reverse proxy",
                )
        except OSError as exc:
            return TrafficFlowCheck(
                name="upstream_connectivity",
                success=False,
                message=f"Cannot reach upstream {host}:{port}: {exc}",
            )

    def test_ssl_readiness(self, app: ProxyAppBase) -> TrafficFlowCheck:
        if not app.force_https:
            return TrafficFlowCheck(
                name="ssl_readiness",
                success=True,
                message="HTTPS redirect not enabled - SSL check skipped",
            )
        domain = app.domains[0]
        cert_path = self.settings.letsencrypt_live / domain / "fullchain.pem"
        if cert_path.exists():
            return TrafficFlowCheck(
                name="ssl_readiness",
                success=True,
                message=f"Certificate found for {domain}",
            )
        return TrafficFlowCheck(
            name="ssl_readiness",
            success=False,
            message=f"No certificate at {cert_path}. Issue cert before enabling force_https.",
        )

    def _isolated_nginx_conf(self, test_dir: Path, site_path: Path) -> str:
        pid_path = test_dir / "nginx.pid"
        error_log = test_dir / "error.log"
        for subdir in ("body", "proxy", "fastcgi", "uwsgi", "scgi"):
            (test_dir / subdir).mkdir(parents=True, exist_ok=True)
        return (
            f"pid {pid_path};\n"
            f"error_log {error_log} warn;\n"
            f"events {{ worker_connections 1024; }}\n"
            f"http {{\n"
            f"    client_body_temp_path {test_dir / 'body'};\n"
            f"    proxy_temp_path {test_dir / 'proxy'};\n"
            f"    fastcgi_temp_path {test_dir / 'fastcgi'};\n"
            f"    uwsgi_temp_path {test_dir / 'uwsgi'};\n"
            f"    scgi_temp_path {test_dir / 'scgi'};\n"
            f"    include {site_path};\n"
            f"}}\n"
        )

    def test_config_syntax(self, app: ProxyAppBase) -> TrafficFlowCheck:
        test_root = self.settings.data_dir / "config-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        test_id = uuid.uuid4().hex
        test_dir = test_root / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        site_path = test_dir / "site.conf"
        nginx_conf = test_dir / "nginx.conf"

        try:
            rendered = self.writer.render_config(app)
            site_path.write_text(rendered, encoding="utf-8")
            nginx_conf.write_text(self._isolated_nginx_conf(test_dir, site_path), encoding="utf-8")
            result = subprocess.run(
                self._cmd(self.NGINX_BIN, "-t", "-c", str(nginx_conf)),
                capture_output=True,
                text=True,
                check=False,
            )
            output = (result.stdout or "") + (result.stderr or "")
            if result.returncode == 0:
                return TrafficFlowCheck(
                    name="nginx_syntax",
                    success=True,
                    message="Generated Nginx configuration syntax is valid",
                )
            return TrafficFlowCheck(
                name="nginx_syntax",
                success=False,
                message=output.strip() or "Nginx syntax test failed",
            )
        except Exception as exc:
            return TrafficFlowCheck(
                name="nginx_syntax",
                success=False,
                message=f"Failed to validate config: {exc}",
            )
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_traffic_flow(self, app: ProxyAppBase) -> TrafficFlowTestResult:
        checks = [
            TrafficFlowCheck(
                name="input_validation",
                success=True,
                message=f"Domain(s) {', '.join(app.domains)} and upstream validated",
            ),
            self.test_config_syntax(app),
            self.test_upstream(app.target_host, app.target_port),
            self.test_ssl_readiness(app),
            TrafficFlowCheck(
                name="traffic_path",
                success=True,
                message=(
                    f"Expected flow: Internet → Firewall → Nginx ({self.settings.server_public_ip}) "
                    f"→ {app.domains[0]} → {app.target_protocol.value}://{app.target_host}:{app.target_port}"
                ),
            ),
        ]

        critical = [c for c in checks if c.name in {"nginx_syntax", "upstream_connectivity", "ssl_readiness"}]
        success = all(check.success for check in critical)
        failed = [c.name for c in critical if not c.success]
        if success:
            summary = "Traffic flow test passed - configuration should work when applied."
        else:
            summary = f"Traffic flow test failed: {', '.join(failed)}"

        checks[-1] = TrafficFlowCheck(
            name="traffic_path",
            success=success,
            message=checks[-1].message if success else f"{checks[-1].message} (blocked by failed checks)",
        )

        return TrafficFlowTestResult(success=success, summary=summary, checks=checks)
