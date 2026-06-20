from app.security.encryption import decrypt_value, encrypt_value


def test_encrypt_decrypt_roundtrip(temp_settings):
    encrypted = encrypt_value(temp_settings, "secret-password")
    assert encrypted
    assert decrypt_value(temp_settings, encrypted) == "secret-password"
