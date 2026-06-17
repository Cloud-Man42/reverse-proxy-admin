import pytest
from fastapi import HTTPException

from app.models.user import User
from app.security.permissions import Permission, require_permission


def test_user_permissions_matrix():
    admin = User(username="admin", password_hash="x", is_admin=True)
    viewer = User(username="view", password_hash="x", perm_read=True)
    editor = User(username="edit", password_hash="x", perm_read=True, perm_edit=True)

    assert admin.has_read() and admin.has_create() and admin.has_edit()
    assert viewer.has_read() and not viewer.has_create()
    assert editor.has_edit() and not editor.has_create()


@pytest.mark.asyncio
async def test_viewer_denied_create_permission():
    viewer = User(username="view", password_hash="x", perm_read=True, is_active=True)
    checker = require_permission(Permission.CREATE)
    with pytest.raises(HTTPException) as exc:
        await checker(user=viewer)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_editor_has_read_permission():
    editor = User(username="edit", password_hash="x", perm_read=True, perm_edit=True, is_active=True)
    checker = require_permission(Permission.READ)
    user = await checker(user=editor)
    assert user.username == "edit"
