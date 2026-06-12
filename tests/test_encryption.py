import pytest
from cryptography.fernet import Fernet

from app.core.encryption import EncryptionError, decrypt_text, encrypt_text


def test_fernet_encrypts_and_decrypts_text() -> None:
    key = Fernet.generate_key().decode()
    cipher_text = encrypt_text("private cookie data", key)

    assert cipher_text != "private cookie data"
    assert decrypt_text(cipher_text, key) == "private cookie data"


def test_invalid_encryption_key_is_rejected() -> None:
    with pytest.raises(EncryptionError, match="key is invalid"):
        encrypt_text("data", "not-a-fernet-key")
