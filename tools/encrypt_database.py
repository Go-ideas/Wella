from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from cryptography.hazmat.primitives import constant_time

# Allow running directly from tools/ without installing a package.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from secure_io import encrypt_sqlite_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Cifra una base analítica SQLite para el simulador Go Ideas.")
    parser.add_argument("input_db", help="Ruta del archivo .db analítico")
    parser.add_argument("output_file", help="Ruta de salida .goideas")
    args = parser.parse_args()

    src = Path(args.input_db)
    dst = Path(args.output_file)
    if not src.exists():
        raise SystemExit(f"No existe: {src}")
    if dst.suffix.lower() != ".goideas":
        raise SystemExit("La salida debe terminar en .goideas")

    p1 = getpass.getpass("Clave de cifrado (mínimo 10 caracteres): ")
    p2 = getpass.getpass("Repite la clave: ")
    if not constant_time.bytes_eq(p1.encode(), p2.encode()):
        raise SystemExit("Las claves no coinciden.")

    blob = encrypt_sqlite_bytes(src.read_bytes(), p1, salt=os.urandom(16), nonce=os.urandom(12))
    dst.write_bytes(blob)
    print(f"Archivo cifrado generado: {dst}")
    print("Entrega el .goideas y la clave por canales separados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
