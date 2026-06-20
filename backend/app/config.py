from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Nginx Reverse Proxy Admin"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    host: str = "127.0.0.1"
    port: int = 8080

    database_url: str = "sqlite:////var/lib/reverse-proxy-admin/app.db"
    data_dir: Path = Path("/var/lib/reverse-proxy-admin")
    backup_dir: Path = Path("/var/lib/reverse-proxy-admin/backups")

    nginx_sites_available: Path = Path("/etc/nginx/sites-available")
    nginx_sites_enabled: Path = Path("/etc/nginx/sites-enabled")
    nginx_error_log: Path = Path("/var/log/nginx/error.log")
    nginx_access_log: Path = Path("/var/log/nginx/access.log")
    letsencrypt_live: Path = Path("/etc/letsencrypt/live")
    certbot_config_dir: Path = Path("/etc/letsencrypt")
    certbot_work_dir: Path = Path("/var/lib/reverse-proxy-admin/certbot/work")
    certbot_logs_dir: Path = Path("/var/lib/reverse-proxy-admin/certbot/logs")
    htpasswd_dir: Path = Path("/etc/nginx/.htpasswd")

    excluded_config_files: List[str] = Field(default_factory=lambda: ["admin-ui.conf", "default"])

    session_cookie_name: str = "nginx_admin_session"
    csrf_cookie_name: str = "nginx_admin_csrf"
    session_max_age_seconds: int = 86400

    admin_username: str = "admin"
    admin_password: str = ""

    certbot_email: str = ""
    certbot_expiring_days: int = 30

    allowed_ips: List[str] = Field(default_factory=lambda: ["127.0.0.1", "::1", "10.0.0.0/24"])
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 900

    use_sudo: bool = True
    nginx_reload_mode: str = "systemctl"
    frontend_dist: Path = Path("/opt/reverse-proxy-admin/frontend/dist")

    server_public_ip: str = "203.0.113.1"
    server_hostname: str = "reverse-proxy"
    network_exposed_ports: List[int] = Field(default_factory=lambda: [80, 443, 8443])
    admin_ui_port: int = 8443
    admin_ui_require_https: bool = True

    encryption_key: str = ""
    alembic_upgrade: bool = True
    scheduler_enabled: bool = True
    health_check_interval_seconds: int = 60
    nginx_regen_debounce_seconds: int = 10
    nginx_regen_check_interval_seconds: int = 5
    system_monitor_interval_seconds: int = 300
    ssl_alert_interval_seconds: int = 86400
    health_warning_ms: int = 2000
    proxy_traffic_interval_seconds: int = 60
    status_report_check_interval_seconds: int = 3600
    threat_feed_sync_interval_seconds: int = 3600

    @property
    def security_dir(self) -> Path:
        return self.data_dir / "security"

    @field_validator("data_dir", "backup_dir", mode="before")
    @classmethod
    def expand_paths(cls, value: Path | str) -> Path:
        return Path(value).expanduser()

    def ensure_certbot_dirs(self) -> None:
        self.certbot_work_dir.mkdir(parents=True, exist_ok=True)
        self.certbot_logs_dir.mkdir(parents=True, exist_ok=True)

    def allowed_read_paths(self) -> List[Path]:
        return [
            self.nginx_sites_available,
            self.nginx_sites_enabled,
            self.nginx_error_log.parent,
            self.letsencrypt_live,
            self.data_dir,
            self.htpasswd_dir,
        ]

    def allowed_write_paths(self) -> List[Path]:
        return [
            self.nginx_sites_available,
            self.nginx_sites_enabled,
            self.data_dir,
            self.backup_dir,
            self.htpasswd_dir,
            self.security_dir,
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
