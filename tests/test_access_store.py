import json

from app.core.access_store import (
    add_allowed_user,
    is_runtime_allowed,
    list_allowed_users,
    load_allowed_users,
    remove_allowed_user,
)


def test_loading_empty_allowlist(tmp_path) -> None:
    assert load_allowed_users(tmp_path / "allowed_users.json") == []


def test_adds_and_lists_allowed_user(tmp_path) -> None:
    path = tmp_path / "access" / "allowed_users.json"

    assert add_allowed_user(path, 123, added_by=1, note="tester")
    users = list_allowed_users(path)

    assert users[0].telegram_id == 123
    assert users[0].note == "tester"
    assert users[0].added_by == 1
    assert is_runtime_allowed(path, 123)


def test_removes_allowed_user(tmp_path) -> None:
    path = tmp_path / "allowed_users.json"
    add_allowed_user(path, 123, added_by=1)

    assert remove_allowed_user(path, 123)
    assert not remove_allowed_user(path, 123)
    assert load_allowed_users(path) == []


def test_duplicate_add_does_not_create_duplicate(tmp_path) -> None:
    path = tmp_path / "allowed_users.json"

    assert add_allowed_user(path, 123, added_by=1)
    assert not add_allowed_user(path, 123, added_by=2, note="duplicate")
    assert len(load_allowed_users(path)) == 1


def test_save_is_atomic_and_leaves_no_temporary_file(tmp_path) -> None:
    path = tmp_path / "allowed_users.json"
    add_allowed_user(path, 123, added_by=1)

    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    assert json.loads(path.read_text("utf-8"))["allowed_users"][0][
        "telegram_id"
    ] == 123
