from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inversiones.db"


def crear_tablas():
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            ticker TEXT NOT NULL,
            precio REAL NOT NULL,
            moneda TEXT DEFAULT 'ARS',
            fuente TEXT,
            archivo_origen TEXT,
            hash_precio TEXT UNIQUE,
            fecha_ingesta TEXT
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    crear_tablas()
    print(f"Base creada correctamente en: {DB_PATH}")
