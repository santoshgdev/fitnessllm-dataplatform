"""Task utils."""
import base64
from datetime import datetime

import pytz
from beartype import beartype
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def update_last_refresh() -> datetime:
    """Return the current time."""
    pacific_tz = pytz.timezone("America/Los_Angeles")
    return datetime.now(pacific_tz)


@beartype
def decrypt_token(encrypted_token: str, key: str) -> str:
    """Decrypt a token that was encrypted using AES-256-CBC in JavaScript.

    Args:
        encrypted_token (str): The encrypted token in format "iv:encrypted"
        key (str or bytes): The encryption key

    Returns:
        str: The decrypted token
    """
    # Split the IV and encrypted data
    parts = encrypted_token.split(":")
    if len(parts) != 2:
        raise ValueError("Invalid encrypted token format")

    # Decode IV and encrypted data from base64
    iv = base64.b64decode(parts[0])
    encrypted_data = base64.b64decode(parts[1])

    # Prepare the key (ensure its bytes)
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key

    # For AES-256-CBC, the key must be 32 bytes
    if len(key_bytes) != 32:
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b"\0")  # Pad with zeros
        else:
            key_bytes = key_bytes[:32]  # Truncate

    # Create decipher
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    # Decrypt
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Remove padding (PKCS#7 padding is used by default in AES-CBC)
    padding_length = decrypted_data[-1]
    if 0 < padding_length <= 16:  # Sanity check for padding
        decrypted_data = decrypted_data[:-padding_length]

    # Return as string
    return decrypted_data.decode("utf-8")
