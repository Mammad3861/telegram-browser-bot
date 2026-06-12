from cryptography.fernet import Fernet, InvalidToken


class EncryptionError(ValueError):
    pass


def _fernet(key: str) -> Fernet:
    if not key:
        raise EncryptionError("Cookie encryption key is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise EncryptionError("Cookie encryption key is invalid") from exc


def encrypt_text(plain_text: str, key: str) -> str:
    return _fernet(key).encrypt(plain_text.encode("utf-8")).decode("ascii")


def decrypt_text(cipher_text: str, key: str) -> str:
    try:
        return _fernet(key).decrypt(cipher_text.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, UnicodeDecodeError) as exc:
        raise EncryptionError("Encrypted session data could not be decrypted") from exc
