import re
import shutil
import socket
import subprocess
import uuid
from pathlib import Path

from app.config import Settings
from app.schemas import ProxyAppBase, TrafficFlowCheck, TrafficFlowTestResult
from app.services.cert_paths import certificate_exists, certificate_exists_message, _sudo_path_is_file
from app.services.nginx_writer import NginxWriter, PROXY_DEBUG_LOG_FORMAT


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
        host = host.strip()
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

    def test_upstream_routes(self, app: ProxyAppBase) -> TrafficFlowCheck:
        failures: list[str] = []
        for route in app.routes:
            check = self.test_upstream(route.target_host, route.target_port)
            if not check.success:
                failures.append(f"{route.path_prefix} -> {route.target_host}:{route.target_port}")
        if failures:
            return TrafficFlowCheck(
                name="upstream_connectivity",
                success=False,
                message="Cannot reach upstream(s): " + "; ".join(failures),
            )
        if len(app.routes) == 1:
            route = app.routes[0]
            return TrafficFlowCheck(
                name="upstream_connectivity",
                success=True,
                message=f"Upstream {route.target_host}:{route.target_port} is reachable from reverse proxy",
            )
        return TrafficFlowCheck(
            name="upstream_connectivity",
            success=True,
            message=f"All {len(app.routes)} upstream route(s) are reachable from reverse proxy",
        )

    def test_ssl_readiness(self, app: ProxyAppBase) -> TrafficFlowCheck:
        if not app.force_https:
            return TrafficFlowCheck(
                name="ssl_readiness",
                success=True,
                message="HTTPS redirect not enabled - SSL check skipped",
            )
        domain = app.domains[0]
        ok, message = certificate_exists_message(self.settings, domain)
        return TrafficFlowCheck(name="ssl_readiness", success=ok, message=message)

    def _prepare_rendered_for_syntax_test(self, rendered: str, test_dir: Path, app: ProxyAppBase) -> str:
        access_log_path = (test_dir / "access.log").as_posix()
        rendered = re.sub(
            r"access_log\s+/var/log/nginx/[^\s;]+",
            lambda _match: f"access_log {access_log_path}",
            rendered,
        )
        if not app.force_https:
            return rendered

        domain = app.domains[0]
        if certificate_exists(self.settings, domain):
            return self._sanitize_ssl_includes_for_syntax_test(rendered)

        return self._rendered_config_for_syntax_test(rendered, test_dir, app)

    def _sanitize_ssl_includes_for_syntax_test(self, rendered: str) -> str:
        options = Path("/etc/letsencrypt/options-ssl-nginx.conf")
        dhparam = Path("/etc/letsencrypt/ssl-dhparams.pem")
        if not _sudo_path_is_file(self.settings, options):
            rendered = rendered.replace(
                "include /etc/letsencrypt/options-ssl-nginx.conf;",
                "ssl_protocols TLSv1.2 TLSv1.3;",
            )
        if not _sudo_path_is_file(self.settings, dhparam):
            rendered = rendered.replace("ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;", "")
        return rendered

    def _isolated_nginx_conf(self, test_dir: Path, site_path: Path) -> str:
        pid_path = test_dir / "nginx.pid"
        error_log = test_dir / "error.log"
        for subdir in ("body", "proxy", "fastcgi", "uwsgi", "scgi"):
            (test_dir / subdir).mkdir(parents=True, exist_ok=True)

        mime_include = ""
        mime_types = Path("/etc/nginx/mime.types")
        if mime_types.is_file():
            mime_include = f"    include {mime_types};\n    default_type application/octet-stream;\n"

        return (
            f"pid {pid_path};\n"
            f"error_log {error_log} warn;\n"
            f"events {{ worker_connections 1024; }}\n"
            f"http {{\n"
            f"    {PROXY_DEBUG_LOG_FORMAT}\n"
            f"{mime_include}"
            f"    client_body_temp_path {test_dir / 'body'};\n"
            f"    proxy_temp_path {test_dir / 'proxy'};\n"
            f"    fastcgi_temp_path {test_dir / 'fastcgi'};\n"
            f"    uwsgi_temp_path {test_dir / 'uwsgi'};\n"
            f"    scgi_temp_path {test_dir / 'scgi'};\n"
            f"    include {site_path};\n"
            f"}}\n"
        )

    def _rendered_config_for_syntax_test(self, rendered: str, test_dir: Path, app: ProxyAppBase) -> str:
        domain = app.domains[0]
        cert_path = test_dir / "syntax-test.crt"
        key_path = test_dir / "syntax-test.key"
        openssl_result = subprocess.run(
            [
                "/usr/bin/openssl",
                "req",
                "-x509",
                "-nodes",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-days",
                "1",
                "-subj",
                f"/CN={domain}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if openssl_result.returncode != 0 or not cert_path.is_file() or not key_path.is_file():
            raise RuntimeError(
                (openssl_result.stderr or openssl_result.stdout or "openssl failed to create temporary certificate").strip()
            )
        live_cert = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        live_key = f"/etc/letsencrypt/live/{domain}/privkey.pem"
        return (
            rendered.replace(live_cert, str(cert_path))
            .replace(live_key, str(key_path))
            .replace("include /etc/letsencrypt/options-ssl-nginx.conf;", "ssl_protocols TLSv1.2 TLSv1.3;")
            .replace("ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;", "")
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
            rendered = self._prepare_rendered_for_syntax_test(rendered, test_dir, app)
            site_path.write_text(rendered, encoding="utf-8")
            nginx_conf.write_text(self._isolated_nginx_conf(test_dir, site_path), encoding="utf-8")
            result = subprocess.run(
                self._cmd(self.NGINX_BIN, "-t", "-c", str(nginx_conf)),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
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
        except subprocess.TimeoutExpired:
            return TrafficFlowCheck(
                name="nginx_syntax",
                success=False,
                message="Nginx syntax test timed out after 30 seconds",
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
        route_summary = ", ".join(
            f"{route.path_prefix} -> {route.target_protocol.value}://{route.target_host}:{route.target_port}"
            for route in app.routes
        )
        checks = [
            TrafficFlowCheck(
                name="input_validation",
                success=True,
                message=f"Domain(s) {', '.join(app.domains)} with routes: {route_summary}",
            ),
            self.test_config_syntax(app),
            self.test_upstream_routes(app),
            self.test_ssl_readiness(app),
            TrafficFlowCheck(
                name="traffic_path",
                success=True,
                message=(
                    f"Expected flow: Internet → Firewall → Nginx ({self.settings.server_public_ip}) "
                    f"→ {app.domains[0]} → [{route_summary}]"
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
