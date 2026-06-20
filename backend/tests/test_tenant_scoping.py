import pytest

from app.models.audit import AuditLog
from app.models.backend_pool import BackendPool
from app.models.notification import NotificationRecipient
from app.models.organization import Organization
from app.models.user import User
from app.schemas import BackendPoolCreate, BackendServerBase, LoadBalancingMethod, NotificationRecipientCreate
from app.security.auth import hash_password
from app.security.tenant_context import bootstrap_default_organization
from app.services.backend_pool_service import BackendPoolService
from app.services.notification_service import NotificationService


@pytest.fixture
def default_org(db_session):
    return bootstrap_default_organization(db_session)


@pytest.fixture
def tenant_orgs(db_session, default_org):
    org_a = Organization(slug="tenant-a", name="Tenant A", enabled=True)
    org_b = Organization(slug="tenant-b", name="Tenant B", enabled=True)
    db_session.add_all([org_a, org_b])
    db_session.commit()
    db_session.refresh(org_a)
    db_session.refresh(org_b)
    return {"default": default_org, "a": org_a, "b": org_b}


def _make_user(db_session, *, username: str, password: str, organization_id: int, role: str) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_active=True,
        is_admin=role in ("super_admin", "tenant_admin"),
        perm_read=True,
        perm_create=role in ("super_admin", "tenant_admin", "operator"),
        perm_edit=role in ("super_admin", "tenant_admin", "operator"),
        organization_id=organization_id,
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def tenant_users(db_session, tenant_orgs):
    return {
        "super_admin": _make_user(
            db_session,
            username="superadmin",
            password="super-pass",
            organization_id=tenant_orgs["default"].id,
            role="super_admin",
        ),
        "tenant_a": _make_user(
            db_session,
            username="tenant-a-user",
            password="tenant-a-pass",
            organization_id=tenant_orgs["a"].id,
            role="tenant_admin",
        ),
        "tenant_b": _make_user(
            db_session,
            username="tenant-b-user",
            password="tenant-b-pass",
            organization_id=tenant_orgs["b"].id,
            role="tenant_admin",
        ),
    }


def _create_pool(db_session, temp_settings, user, name: str, organization_id: int):
    pool = BackendPool(name=name, organization_id=organization_id, load_balancing_method="round_robin")
    db_session.add(pool)
    db_session.commit()
    db_session.refresh(pool)
    return pool


def test_backend_pool_scoping(db_session, temp_settings, tenant_orgs, tenant_users):
    pool_a = _create_pool(db_session, temp_settings, tenant_users["tenant_a"], "pool-a", tenant_orgs["a"].id)
    pool_b = _create_pool(db_session, temp_settings, tenant_users["tenant_b"], "pool-b", tenant_orgs["b"].id)

    super_service = BackendPoolService(temp_settings, db_session, user=tenant_users["super_admin"])
    tenant_a_service = BackendPoolService(temp_settings, db_session, user=tenant_users["tenant_a"])
    tenant_b_service = BackendPoolService(temp_settings, db_session, user=tenant_users["tenant_b"])

    super_pools, super_total = super_service.list_pools()
    assert super_total >= 2
    assert {pool_a.id, pool_b.id}.issubset({pool.id for pool in super_pools})

    tenant_a_pools, tenant_a_total = tenant_a_service.list_pools()
    assert tenant_a_total == 1
    assert tenant_a_pools[0].id == pool_a.id

    tenant_b_pools, tenant_b_total = tenant_b_service.list_pools()
    assert tenant_b_total == 1
    assert tenant_b_pools[0].id == pool_b.id


def test_notification_recipient_scoping(db_session, temp_settings, tenant_orgs, tenant_users):
    NotificationService(temp_settings, db_session, user=tenant_users["tenant_a"]).create_recipient(
        NotificationRecipientCreate(name="A Alerts", email="alerts-a@company.test")
    )
    NotificationService(temp_settings, db_session, user=tenant_users["tenant_b"]).create_recipient(
        NotificationRecipientCreate(name="B Alerts", email="alerts-b@company.test")
    )

    super_recipients = NotificationService(temp_settings, db_session, user=tenant_users["super_admin"]).list_recipients()
    tenant_a_recipients = NotificationService(temp_settings, db_session, user=tenant_users["tenant_a"]).list_recipients()
    tenant_b_recipients = NotificationService(temp_settings, db_session, user=tenant_users["tenant_b"]).list_recipients()

    assert len(super_recipients) >= 2
    assert {item.email for item in super_recipients} >= {"alerts-a@company.test", "alerts-b@company.test"}
    assert [item.email for item in tenant_a_recipients] == ["alerts-a@company.test"]
    assert [item.email for item in tenant_b_recipients] == ["alerts-b@company.test"]


def test_audit_log_scoping(db_session, tenant_orgs, tenant_users):
    db_session.add_all(
        [
            AuditLog(
                username="tenant-a-user",
                action="test",
                resource="resource:a",
                client_ip="127.0.0.1",
                organization_id=tenant_orgs["a"].id,
            ),
            AuditLog(
                username="tenant-b-user",
                action="test",
                resource="resource:b",
                client_ip="127.0.0.1",
                organization_id=tenant_orgs["b"].id,
            ),
        ]
    )
    db_session.commit()

    from app.security.tenant_context import filter_query_by_org

    super_entries = filter_query_by_org(db_session.query(AuditLog), AuditLog, tenant_users["super_admin"]).all()
    tenant_a_entries = filter_query_by_org(db_session.query(AuditLog), AuditLog, tenant_users["tenant_a"]).all()
    tenant_b_entries = filter_query_by_org(db_session.query(AuditLog), AuditLog, tenant_users["tenant_b"]).all()

    assert len(super_entries) >= 2
    assert len(tenant_a_entries) == 1
    assert tenant_a_entries[0].resource == "resource:a"
    assert len(tenant_b_entries) == 1
    assert tenant_b_entries[0].resource == "resource:b"


@pytest.mark.api
def test_organizations_api_super_admin_only(client, db_session, tenant_orgs, tenant_users):
    login = client.post(
        "/api/auth/login",
        json={"username": "superadmin", "password": "super-pass"},
    )
    assert login.status_code == 200
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    response = client.get("/api/organizations", headers=headers, cookies=login.cookies)
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()}
    assert "default" in slugs
    assert "tenant-a" in slugs

    create = client.post(
        "/api/organizations",
        headers=headers,
        cookies=login.cookies,
        json={"slug": "tenant-c", "name": "Tenant C", "enabled": True},
    )
    assert create.status_code == 201
    assert create.json()["slug"] == "tenant-c"


@pytest.mark.api
def test_organizations_api_denied_for_tenant_admin(client, tenant_users):
    login = client.post(
        "/api/auth/login",
        json={"username": "tenant-a-user", "password": "tenant-a-pass"},
    )
    assert login.status_code == 200
    headers = {"X-CSRF-Token": login.json()["csrf_token"]}

    response = client.get("/api/organizations", headers=headers, cookies=login.cookies)
    assert response.status_code == 403


@pytest.mark.api
def test_login_response_includes_org_and_role(client, auth_session):
    response = client.get("/api/auth/me", headers=auth_session["headers"], cookies=auth_session["cookies"])
    assert response.status_code == 200
    data = response.json()
    assert "organization_id" in data
    assert "role" in data
    assert data["role"] == "super_admin"
