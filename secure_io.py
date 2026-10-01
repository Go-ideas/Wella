from __future__ import annotations

import hashlib
import sqlite3
import zlib
from dataclasses import dataclass
from typing import Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"GIDEAS01"
VERSION = 1
VERSION_MULTI = 2
SALT_LEN = 16
NONCE_LEN = 12
DATA_KEY_LEN = 32
WRAPPED_KEY_LEN = DATA_KEY_LEN + 16  # AES-GCM authentication tag
AAD = b"goideas-coloracion-simulator-v1"
AAD_MULTI_DATA = b"goideas-coloracion-simulator-v2:data"
AAD_MULTI_WRAP = b"goideas-coloracion-simulator-v2:key"


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


def _validate_sqlite(sqlite_bytes: bytes) -> None:
    if not sqlite_bytes.startswith(b"SQLite format 3\x00"):
        raise EncryptedPackageError("El archivo de origen no parece ser una base SQLite válida.")


def encrypt_sqlite_bytes(sqlite_bytes: bytes, passphrase: str, *, salt: bytes, nonce: bytes) -> bytes:
    """Encrypt SQLite bytes into the original single-password Go Ideas format (v1).

    Kept for backwards compatibility with existing packages and tests.
    Production callers must provide cryptographically random salt and nonce values.
    """
    _validate_sqlite(sqlite_bytes)
    if len(salt) != SALT_LEN or len(nonce) != NONCE_LEN:
        raise EncryptedPackageError("Salt/nonce inválidos.")
    key = _derive_key(passphrase, salt)
    payload = zlib.compress(sqlite_bytes, level=9)
    ciphertext = AESGCM(key).encrypt(nonce, payload, AAD)
    return MAGIC + bytes([VERSION]) + salt + nonce + ciphertext


def encrypt_sqlite_bytes_multi(
    sqlite_bytes: bytes,
    passphrases: Sequence[str],
    *,
    salts: Sequence[bytes],
    wrap_nonces: Sequence[bytes],
    payload_nonce: bytes,
    data_key: bytes,
) -> bytes:
    """Encrypt one SQLite payload so any authorized passphrase can open it.

    Format v2 encrypts the database once with a random data key. That data key is
    independently wrapped for each passphrase, so no plaintext password or master
    password needs to be stored in the app or repository.
    """
    _validate_sqlite(sqlite_bytes)

    unique_passphrases = list(dict.fromkeys(passphrases))
    if not unique_passphrases:
        raise EncryptedPackageError("Se requiere al menos una clave.")
    if len(unique_passphrases) > 255:
        raise EncryptedPackageError("Demasiadas claves autorizadas.")
    if len(salts) != len(unique_passphrases) or len(wrap_nonces) != len(unique_passphrases):
        raise EncryptedPackageError("La cantidad de salts/nonces no coincide con las claves.")
    if len(payload_nonce) != NONCE_LEN:
        raise EncryptedPackageError("Nonce de contenido inválido.")
    if len(data_key) != DATA_KEY_LEN:
        raise EncryptedPackageError("Clave de datos inválida.")

    recipients = []
    for passphrase, salt, wrap_nonce in zip(unique_passphrases, salts, wrap_nonces):
        if len(salt) != SALT_LEN or len(wrap_nonce) != NONCE_LEN:
            raise EncryptedPackageError("Salt/nonce de clave inválido.")
        wrapping_key = _derive_key(passphrase, salt)
        wrapped_key = AESGCM(wrapping_key).encrypt(wrap_nonce, data_key, AAD_MULTI_WRAP)
        if len(wrapped_key) != WRAPPED_KEY_LEN:
            raise EncryptedPackageError("Longitud de clave envuelta inválida.")
        recipients.append(salt + wrap_nonce + wrapped_key)

    compressed = zlib.compress(sqlite_bytes, level=9)
    ciphertext = AESGCM(data_key).encrypt(payload_nonce, compressed, AAD_MULTI_DATA)

    return (
        MAGIC
        + bytes([VERSION_MULTI])
        + bytes([len(unique_passphrases)])
        + b"".join(recipients)
        + payload_nonce
        + ciphertext
    )


def _decrypt_v1(package_bytes: bytes, passphrase: str) -> bytes:
    min_size = len(MAGIC) + 1 + SALT_LEN + NONCE_LEN + 16
    if len(package_bytes) < min_size:
        raise EncryptedPackageError("El archivo cifrado está vacío o incompleto.")

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
    _validate_sqlite(sqlite_bytes)
    return sqlite_bytes


def _decrypt_v2(package_bytes: bytes, passphrase: str) -> bytes:
    header_size = len(MAGIC) + 2
    if len(package_bytes) < header_size:
        raise EncryptedPackageError("El archivo cifrado está vacío o incompleto.")

    recipient_count = package_bytes[len(MAGIC) + 1]
    if recipient_count < 1:
        raise EncryptedPackageError("El archivo no contiene claves autorizadas.")

    offset = header_size
    recipient_size = SALT_LEN + NONCE_LEN + WRAPPED_KEY_LEN
    min_size = header_size + recipient_count * recipient_size + NONCE_LEN + 16
    if len(package_bytes) < min_size:
        raise EncryptedPackageError("El archivo cifrado está incompleto.")

    data_key = None
    for _ in range(recipient_count):
        salt = package_bytes[offset : offset + SALT_LEN]
        offset += SALT_LEN
        wrap_nonce = package_bytes[offset : offset + NONCE_LEN]
        offset += NONCE_LEN
        wrapped_key = package_bytes[offset : offset + WRAPPED_KEY_LEN]
        offset += WRAPPED_KEY_LEN

        try:
            wrapping_key = _derive_key(passphrase, salt)
            data_key = AESGCM(wrapping_key).decrypt(wrap_nonce, wrapped_key, AAD_MULTI_WRAP)
            break
        except (InvalidTag, EncryptedPackageError):
            data_key = None

    if data_key is None:
        raise EncryptedPackageError("Clave incorrecta o archivo alterado.")

    # Skip any recipients not traversed after the successful slot.
    payload_offset = header_size + recipient_count * recipient_size
    payload_nonce = package_bytes[payload_offset : payload_offset + NONCE_LEN]
    ciphertext = package_bytes[payload_offset + NONCE_LEN :]

    try:
        compressed = AESGCM(data_key).decrypt(payload_nonce, ciphertext, AAD_MULTI_DATA)
    except InvalidTag as exc:
        raise EncryptedPackageError("El contenido cifrado fue alterado.") from exc

    try:
        sqlite_bytes = zlib.decompress(compressed)
    except zlib.error as exc:
        raise EncryptedPackageError("El contenido cifrado no pudo recuperarse.") from exc
    _validate_sqlite(sqlite_bytes)
    return sqlite_bytes


def decrypt_sqlite_bytes(package_bytes: bytes, passphrase: str) -> bytes:
    """Decrypt a .goideas package fully in RAM and return raw SQLite bytes.

    Supports legacy v1 single-password packages and v2 multi-password packages.
    """
    if not package_bytes or len(package_bytes) < len(MAGIC) + 1:
        raise EncryptedPackageError("El archivo cifrado está vacío o incompleto.")
    if package_bytes[: len(MAGIC)] != MAGIC:
        raise EncryptedPackageError("El archivo no corresponde al formato seguro de Go Ideas.")

    version = package_bytes[len(MAGIC)]
    if version == VERSION:
        return _decrypt_v1(package_bytes, passphrase)
    if version == VERSION_MULTI:
        return _decrypt_v2(package_bytes, passphrase)
    raise EncryptedPackageError(f"Versión de archivo no soportada: {version}.")


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
