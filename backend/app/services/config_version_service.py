import difflib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.models.config_version import ConfigVersion
from app.schemas import ConfigVersionCompareResponse, ConfigVersionResponse
from app.services.nginx_ops import NginxOps
from app.services.nginx_writer import NginxWriter

RESOURCE_PROXY = "proxy"


class ConfigVersionService:
    def __init__(self, settings: Settings, db: Session) -> None:
        self.settings = settings
        self.db = db
        self.writer = NginxWriter(settings)
        self.ops = NginxOps(settings)

    @staticmethod
    def _to_response(row: ConfigVersion) -> ConfigVersionResponse:
        return ConfigVersionResponse(
            id=row.id,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            version=row.version,
            username=row.username,
            summary=row.summary,
            has_old_config=row.old_config is not None,
            nginx_test_result=row.nginx_test_result,
            created_at=row.created_at,
        )

    def _next_version(self, resource_type: str, resource_id: str) -> int:
        latest = (
            self.db.query(ConfigVersion.version)
            .filter(
                ConfigVersion.resource_type == resource_type,
                ConfigVersion.resource_id == resource_id,
            )
            .order_by(ConfigVersion.version.desc())
            .first()
        )
        return (latest[0] if latest else 0) + 1

    def record(
        self,
        *,
        resource_type: str,
        resource_id: str,
        username: str,
        summary: str,
        old_config: Optional[str],
        new_config: str,
        nginx_test_result: Optional[str] = None,
    ) -> ConfigVersionResponse:
        row = ConfigVersion(
            resource_type=resource_type,
            resource_id=resource_id,
            version=self._next_version(resource_type, resource_id),
            username=username,
            summary=summary,
            old_config=old_config,
            new_config=new_config,
            nginx_test_result=nginx_test_result,
            created_at=datetime.utcnow(),
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_response(row)

    def list_versions(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> list[ConfigVersionResponse]:
        query = self.db.query(ConfigVersion)
        if resource_type:
            query = query.filter(ConfigVersion.resource_type == resource_type)
        if resource_id:
            query = query.filter(ConfigVersion.resource_id == resource_id)
        rows = query.order_by(ConfigVersion.created_at.desc(), ConfigVersion.version.desc()).all()
        return [self._to_response(row) for row in rows]

    def get(self, version_id: int) -> Optional[ConfigVersionResponse]:
        row = self.db.get(ConfigVersion, version_id)
        return self._to_response(row) if row else None

    def get_detail(self, version_id: int) -> Optional[ConfigVersion]:
        return self.db.get(ConfigVersion, version_id)

    def compare(self, id1: int, id2: int) -> Optional[ConfigVersionCompareResponse]:
        left = self.db.get(ConfigVersion, id1)
        right = self.db.get(ConfigVersion, id2)
        if not left or not right:
            return None
        diff = difflib.unified_diff(
            (left.new_config or "").splitlines(),
            (right.new_config or "").splitlines(),
            fromfile=f"v{left.version}",
            tofile=f"v{right.version}",
            lineterm="",
        )
        return ConfigVersionCompareResponse(
            id1=id1,
            id2=id2,
            resource_type=left.resource_type,
            resource_id=left.resource_id,
            version1=left.version,
            version2=right.version,
            diff="\n".join(diff),
        )

    def rollback(self, version_id: int, username: str) -> tuple[bool, str, Optional[ConfigVersionResponse]]:
        version = self.db.get(ConfigVersion, version_id)
        if version is None:
            return False, "Config version not found", None
        if version.resource_type != RESOURCE_PROXY:
            return False, f"Rollback not supported for resource type {version.resource_type}", None

        path = self.writer.config_path_for(version.resource_id)
        current_config = path.read_text(encoding="utf-8") if path.exists() else None
        target_config = version.old_config

        if target_config is None:
            if not path.exists():
                return False, "Proxy config file not found", None

            def write_fn() -> None:
                self.ops.disable_site(path.name)
                path.unlink(missing_ok=True)

            ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
            if not ok:
                return False, output, None
            reload_ok, reload_output = self.ops.reload()
            if not reload_ok:
                return False, reload_output, None
            recorded = self.record(
                resource_type=version.resource_type,
                resource_id=version.resource_id,
                username=username,
                summary=f"Rollback to before version {version.version}",
                old_config=current_config,
                new_config="",
                nginx_test_result=reload_output,
            )
            return True, reload_output, recorded

        def write_fn() -> None:
            self.writer.atomic_write(path, target_config)
            self.ops.enable_site(path.name)

        ok, output = self.writer.apply_change(path, write_fn, self.ops.test_config)
        if not ok:
            return False, output, None
        reload_ok, reload_output = self.ops.reload()
        if not reload_ok:
            return False, reload_output, None
        recorded = self.record(
            resource_type=version.resource_type,
            resource_id=version.resource_id,
            username=username,
            summary=f"Rollback to version {version.version - 1 if version.version > 1 else 0} state",
            old_config=current_config,
            new_config=target_config,
            nginx_test_result=reload_output,
        )
        return True, reload_output, recorded
