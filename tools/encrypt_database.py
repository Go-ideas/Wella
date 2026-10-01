from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from cryptography.hazmat.primitives import constant_time

# Allow running directly from tools/ without installing a package.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from secure_io import encrypt_sqlite_bytes, encrypt_sqlite_bytes_multi


def _prompt_passphrase(label: str) -> str:
    p1 = getpass.getpass(f"{label} (mínimo 10 caracteres): ")
    p2 = getpass.getpass(f"Repite {label.lower()}: ")
    if not constant_time.bytes_eq(p1.encode(), p2.encode()):
        raise SystemExit("Las claves no coinciden.")
    return p1


def main() -> int:
    parser = argparse.ArgumentParser(description="Cifra una base analítica SQLite para el simulador Go Ideas.")
    parser.add_argument("input_db", help="Ruta del archivo .db analítico")
    parser.add_argument("output_file", help="Ruta de salida .goideas")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Permite autorizar más de una contraseña sobre el mismo archivo cifrado.",
    )
    args = parser.parse_args()

    src = Path(args.input_db)
    dst = Path(args.output_file)
    if not src.exists():
        raise SystemExit(f"No existe: {src}")
    if dst.suffix.lower() != ".goideas":
        raise SystemExit("La salida debe terminar en .goideas")

    primary = _prompt_passphrase("Clave principal")

    if args.multi:
        passphrases = [primary]
        while True:
            extra = getpass.getpass("Clave alternativa adicional (Enter para terminar): ")
            if not extra:
                break
            if len(extra) < 10:
                raise SystemExit("Cada clave debe contener al menos 10 caracteres.")
            repeat = getpass.getpass("Repite la clave alternativa: ")
            if not constant_time.bytes_eq(extra.encode(), repeat.encode()):
                raise SystemExit("Las claves no coinciden.")
            if extra not in passphrases:
                passphrases.append(extra)

        blob = encrypt_sqlite_bytes_multi(
            src.read_bytes(),
            passphrases,
            salts=[os.urandom(16) for _ in passphrases],
            wrap_nonces=[os.urandom(12) for _ in passphrases],
            payload_nonce=os.urandom(12),
            data_key=os.urandom(32),
        )
        print(f"Archivo cifrado generado con {len(passphrases)} claves autorizadas: {dst}")
    else:
        blob = encrypt_sqlite_bytes(
            src.read_bytes(),
            primary,
            salt=os.urandom(16),
            nonce=os.urandom(12),
        )
        print(f"Archivo cifrado generado: {dst}")

    dst.write_bytes(blob)
    print("Entrega el .goideas y las claves por canales separados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
