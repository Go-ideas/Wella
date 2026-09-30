from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from secure_io import EncryptedPackageError, decrypt_sqlite_bytes, encrypt_sqlite_bytes, sqlite_connection_from_bytes


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
