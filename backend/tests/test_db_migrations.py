from sqlalchemy import create_engine, inspect, text


def test_migrate_smtp_columns_adds_missing_fields(tmp_path, monkeypatch):
    from app import db as db_module

    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'migrate-test.db'}",
        connect_args={"check_same_thread": False},
    )
    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE smtp_settings (
                    id INTEGER PRIMARY KEY,
                    host VARCHAR(255) DEFAULT '',
                    port INTEGER DEFAULT 587
                )
                """
            )
        )

    monkeypatch.setattr(db_module, "engine", test_engine)
    db_module.migrate_smtp_columns()

    columns = {col["name"] for col in inspect(test_engine).get_columns("smtp_settings")}
    assert "tls_server_name" in columns
    assert "verify_tls_certificate" in columns
