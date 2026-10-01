from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from secure_io import (
    EncryptedPackageError,
    decrypt_sqlite_bytes,
    encrypt_sqlite_bytes,
    encrypt_sqlite_bytes_multi,
    sqlite_connection_from_bytes,
)


def make_db() -> bytes:
    con = sqlite3.connect(":memory:")
    con.execute("create table t(x integer)")
    con.execute("insert into t values (42)")
    data = con.serialize()
    con.close()
    return data


def test_round_trip_and_memory_sqlite():
    raw = make_db()
    encrypted = encrypt_sqlite_bytes(raw, "Clave-Segura-123", salt=b"1" * 16, nonce=b"2" * 12)
    assert not encrypted.startswith(b"SQLite format 3")
    recovered = decrypt_sqlite_bytes(encrypted, "Clave-Segura-123")
    assert recovered == raw
    con = sqlite_connection_from_bytes(recovered)
    try:
        assert con.execute("select x from t").fetchone()[0] == 42
    finally:
        con.close()


def test_wrong_password_fails():
    raw = make_db()
    encrypted = encrypt_sqlite_bytes(raw, "Clave-Segura-123", salt=b"1" * 16, nonce=b"2" * 12)
    with pytest.raises(EncryptedPackageError):
        decrypt_sqlite_bytes(encrypted, "Clave-Incorrecta-999")



def test_multi_password_package_accepts_each_authorized_key():
    raw = make_db()
    encrypted = encrypt_sqlite_bytes_multi(
        raw,
        ["Clave-Principal-123", "Clave-Alterna-456"],
        salts=[b"a" * 16, b"b" * 16],
        wrap_nonces=[b"c" * 12, b"d" * 12],
        payload_nonce=b"e" * 12,
        data_key=b"f" * 32,
    )
    assert decrypt_sqlite_bytes(encrypted, "Clave-Principal-123") == raw
    assert decrypt_sqlite_bytes(encrypted, "Clave-Alterna-456") == raw


def test_multi_password_package_rejects_unknown_key():
    raw = make_db()
    encrypted = encrypt_sqlite_bytes_multi(
        raw,
        ["Clave-Principal-123", "Clave-Alterna-456"],
        salts=[b"a" * 16, b"b" * 16],
        wrap_nonces=[b"c" * 12, b"d" * 12],
        payload_nonce=b"e" * 12,
        data_key=b"f" * 32,
    )
    with pytest.raises(EncryptedPackageError):
        decrypt_sqlite_bytes(encrypted, "Clave-No-Autorizada-999")
