import base64
import hashlib
import hmac
import os

PREFIX = "ncsec:v1:"


def is_encrypted_secret(value) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_secret(value: str, secret_key: str) -> str:
    if value == "":
        return ""
    if is_encrypted_secret(value):
        return value

    salt = os.urandom(16)
    nonce = os.urandom(16)
    plaintext = value.encode("utf-8")
    enc_key, mac_key = _derive_keys(secret_key, salt)
    ciphertext = _xor_bytes(plaintext, _keystream(enc_key, nonce, len(plaintext)))
    tag = hmac.new(mac_key, b"v1" + salt + nonce + ciphertext, hashlib.sha256).digest()
    payload = salt + nonce + tag + ciphertext
    return PREFIX + base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_secret(value: str, secret_key: str) -> str:
    if not is_encrypted_secret(value):
        return value

    try:
        payload = base64.urlsafe_b64decode(value[len(PREFIX) :].encode("ascii"))
    except Exception as exc:
        raise ValueError("Invalid encrypted secret") from exc

    if len(payload) < 64:
        raise ValueError("Invalid encrypted secret")

    salt = payload[:16]
    nonce = payload[16:32]
    tag = payload[32:64]
    ciphertext = payload[64:]
    enc_key, mac_key = _derive_keys(secret_key, salt)
    expected = hmac.new(mac_key, b"v1" + salt + nonce + ciphertext, hashlib.sha256).digest()

    if not hmac.compare_digest(tag, expected):
        raise ValueError("Encrypted secret could not be verified")

    plaintext = _xor_bytes(ciphertext, _keystream(enc_key, nonce, len(ciphertext)))
    return plaintext.decode("utf-8")


def _derive_keys(secret_key: str, salt: bytes) -> tuple[bytes, bytes]:
    root = hashlib.pbkdf2_hmac("sha256", secret_key.encode("utf-8"), salt, 200_000, dklen=64)
    return root[:32], root[32:]


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        counter_bytes = counter.to_bytes(8, "big")
        blocks.append(hmac.new(key, nonce + counter_bytes, hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))
