from __future__ import annotations

import hashlib
import sqlite3
import zlib
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"GIDEAS01"
VERSION = 1
SALT_LEN = 16
NONCE_LEN = 12
AAD = b"goideas-coloracion-simulator-v1"


class EncryptedPackageError(Exception):
    """Raised when an encrypted client package is invalid or cannot be decrypted."""


@dataclass(frozen=True)
class PackageHeader:
    version: int
    salt: bytes
    nonce: bytes


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or len(passphrase) < 10:
        raise EncryptedPackageError("La clave debe contener al menos 10 caracteres.")
    kdf = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_sqlite_bytes(sqlite_bytes: bytes, passphrase: str, *, salt: bytes, nonce: bytes) -> bytes:
    """Encrypt SQLite bytes into the Go Ideas container format.

    Salt and nonce are explicit to keep the primitive deterministic under test.
    Production callers must provide cryptographically random values.
    """
    if not sqlite_bytes.startswith(b"SQLite format 3\x00"):
        raise EncryptedPackageError("El archivo de origen no parece ser una base SQLite válida.")
    if len(salt) != SALT_LEN or len(nonce) != NONCE_LEN:
        raise EncryptedPackageError("Salt/nonce inválidos.")
    key = _derive_key(passphrase, salt)
    payload = zlib.compress(sqlite_bytes, level=9)
    ciphertext = AESGCM(key).encrypt(nonce, payload, AAD)
    return MAGIC + bytes([VERSION]) + salt + nonce + ciphertext


def decrypt_sqlite_bytes(package_bytes: bytes, passphrase: str) -> bytes:
    """Decrypt a .goideas package fully in RAM and return raw SQLite bytes."""
    min_size = len(MAGIC) + 1 + SALT_LEN + NONCE_LEN + 16
    if not package_bytes or len(package_bytes) < min_size:
        raise EncryptedPackageError("El archivo cifrado está vacío o incompleto.")
    if package_bytes[: len(MAGIC)] != MAGIC:
        raise EncryptedPackageError("El archivo no corresponde al formato seguro de Go Ideas.")
    version = package_bytes[len(MAGIC)]
    if version != VERSION:
        raise EncryptedPackageError(f"Versión de archivo no soportada: {version}.")
    offset = len(MAGIC) + 1
    salt = package_bytes[offset : offset + SALT_LEN]
    offset += SALT_LEN
    nonce = package_bytes[offset : offset + NONCE_LEN]
    offset += NONCE_LEN
    ciphertext = package_bytes[offset:]
    key = _derive_key(passphrase, salt)
    try:
        compressed = AESGCM(key).decrypt(nonce, ciphertext, AAD)
    except InvalidTag as exc:
        raise EncryptedPackageError("Clave incorrecta o archivo alterado.") from exc
    try:
        sqlite_bytes = zlib.decompress(compressed)
    except zlib.error as exc:
        raise EncryptedPackageError("El contenido cifrado no pudo recuperarse.") from exc
    if not sqlite_bytes.startswith(b"SQLite format 3\x00"):
        raise EncryptedPackageError("El contenido descifrado no es una base SQLite válida.")
    return sqlite_bytes


def sqlite_connection_from_bytes(sqlite_bytes: bytes) -> sqlite3.Connection:
    """Open uploaded SQLite bytes in an in-memory SQLite connection.

    No plaintext database file is written to disk. This requires Python's
    sqlite3.Connection.deserialize, available in supported Community Cloud runtimes.
    """
    con = sqlite3.connect(":memory:")
    if not hasattr(con, "deserialize"):
        con.close()
        raise EncryptedPackageError(
            "El runtime no soporta SQLite en memoria (deserialize). No se usará un archivo temporal por seguridad."
        )
    try:
        con.deserialize(sqlite_bytes)
    except Exception:
        con.close()
        raise
    return con


def package_fingerprint(package_bytes: bytes) -> str:
    return hashlib.sha256(package_bytes).hexdigest()
