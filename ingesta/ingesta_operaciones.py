import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "inversiones.db"
CARPETA_OPERACIONES = BASE_DIR / "data" / "operaciones"


def crear_hash_operacion(row):
    texto = "|".join([
        str(row["fecha_operacion"]),
        str(row["ticker"]),
        str(row["operacion"]),
        str(row["cantidad"]),
        str(row["precio_unitario"]),
        str(row["monto_total"]),
        str(row.get("archivo_origen", "")),
    ])
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def crear_tabla_operaciones():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_operacion TEXT NOT NULL,
            ticker TEXT NOT NULL,
            nombre TEXT,
            tipo_activo TEXT,
            operacion TEXT NOT NULL,
            cantidad REAL NOT NULL,
            precio_unitario REAL NOT NULL,
            monto_total REAL NOT NULL,
            moneda TEXT DEFAULT 'ARS',
            comisiones REAL DEFAULT 0,
            fuente TEXT,
            archivo_origen TEXT,
            hash_operacion TEXT UNIQUE,
            fecha_ingesta TEXT
        )
    """)
    conn.commit()
    conn.close()


def leer_archivo(ruta):
    if ruta.suffix.lower() == ".csv":
        return pd.read_csv(ruta)
    if ruta.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(ruta)
    return None


def normalizar_operaciones(df, archivo_origen):
    columnas_requeridas = [
        "fecha_operacion", "ticker", "operacion", "cantidad",
        "precio_unitario", "monto_total"
    ]
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {archivo_origen}: {faltantes}")

    out = pd.DataFrame()
    out["fecha_operacion"] = pd.to_datetime(df["fecha_operacion"]).dt.strftime("%Y-%m-%d")
    out["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    out["nombre"] = df.get("nombre", out["ticker"])
    out["tipo_activo"] = df.get("tipo_activo", "Sin clasificar")
    out["operacion"] = df["operacion"].astype(str).str.upper().str.strip()
    out["cantidad"] = df["cantidad"].astype(float)
    out["precio_unitario"] = df["precio_unitario"].astype(float)
    out["monto_total"] = df["monto_total"].astype(float)
    out["moneda"] = df.get("moneda", "ARS")
    out["comisiones"] = df.get("comisiones", 0).astype(float) if "comisiones" in df.columns else 0
    out["fuente"] = df.get("fuente", "CSV")
    out["archivo_origen"] = archivo_origen
    out["fecha_ingesta"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out["hash_operacion"] = out.apply(crear_hash_operacion, axis=1)
    return out


def insertar_operaciones(df):
    conn = sqlite3.connect(DB_PATH)
    insertados = 0
    for _, row in df.iterrows():
        try:
            row.to_frame().T.to_sql("operaciones", conn, if_exists="append", index=False)
            insertados += 1
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return insertados


def ingestar_operaciones():
    crear_tabla_operaciones()
    CARPETA_OPERACIONES.mkdir(parents=True, exist_ok=True)
    total = 0
    for archivo in CARPETA_OPERACIONES.iterdir():
        if archivo.suffix.lower() not in [".csv", ".xlsx", ".xls"]:
            continue
        df = leer_archivo(archivo)
        if df is None:
            continue
        normalizado = normalizar_operaciones(df, archivo.name)
        insertados = insertar_operaciones(normalizado)
        print(f"{archivo.name}: {insertados} operaciones nuevas")
        total += insertados
    print(f"Total operaciones nuevas: {total}")
    return total


if __name__ == "__main__":
    ingestar_operaciones()
