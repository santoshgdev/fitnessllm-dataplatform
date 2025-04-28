"""Task utils."""
import base64
import os

from beartype import beartype
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

@beartype
def encrypt_token(token: str, key: str) -> str:
    """Encrypt a token using AES-256-CBC with PKCS#7 padding.

    Args:
        token (str): The plaintext token to be encrypted.
        key (str): The encryption key. This key will be encoded as UTF-8 and adjusted to 32 bytes.

    Returns:
        str: The encrypted token in the format "iv:encrypted", where both the IV and the ciphertext are base64-encoded.
    """
    # Convert the plaintext token to bytes.
    token_bytes = token.encode("utf-8")

    # Convert the key to bytes if necessary.
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key

    # Ensure the key is exactly 32 bytes long (AES-256 requirement).
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"\0")  # Pad with zeros.
    elif len(key_bytes) > 32:
        key_bytes = key_bytes[:32]  # Truncate if longer than 32 bytes.

    # Generate a random 16-byte initialization vector (IV).
    iv = os.urandom(16)

    # Apply PKCS#7 padding to the plaintext token.
    padder = padding.PKCS7(
        128
    ).padder()  # The block size is 128 bits (16 bytes) for AES.
    padded_data = padder.update(token_bytes) + padder.finalize()

    # Create the AES cipher in CBC mode.
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Base64-encode the IV and encrypted data.
    iv_encoded = base64.b64encode(iv).decode("utf-8")
    encrypted_encoded = base64.b64encode(encrypted_data).decode("utf-8")

    # Return the combined result in the format "iv:encrypted".
    return f"{iv_encoded}:{encrypted_encoded}"