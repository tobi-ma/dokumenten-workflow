"""Helper script to encrypt a GitHub token for use in the app.

Run this locally:
    python encrypt_token.py

It will ask for your GitHub token and a password, then output the
encrypted token and salt to paste into app/config.py.
"""

import base64
import hashlib
import getpass

from cryptography.fernet import Fernet


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from a password + salt."""
    raw = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.urlsafe_b64encode(raw)


def encrypt_token(token: str, password: str) -> tuple[str, str]:
    """Encrypt a token. Returns (encrypted_token_b64, salt_b64)."""
    import os
    salt = os.urandom(16)
    key = derive_key(password, salt)
    encrypted = Fernet(key).encrypt(token.encode())
    return encrypted.decode(), base64.b64encode(salt).decode()


def main():
    print("=== GitHub Token verschlüsseln ===\n")
    token = getpass.getpass("GitHub Token (wird nicht angezeigt): ")
    if not token.strip():
        print("Kein Token eingegeben.")
        return

    password = getpass.getpass("Passwort zum Verschlüsseln: ")
    confirm = getpass.getpass("Passwort bestätigen: ")
    if password != confirm:
        print("Passwörter stimmen nicht überein.")
        return

    encrypted, salt = encrypt_token(token.strip(), password)

    print("\n--- In app/config.py eintragen: ---\n")
    print(f'ENCRYPTED_GITHUB_TOKEN = "{encrypted}"')
    print(f'TOKEN_SALT = "{salt}"')
    print()


if __name__ == "__main__":
    main()
