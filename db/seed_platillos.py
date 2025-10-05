from pathlib import Path
import sys

# Make project root importable when running this script directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.model.neonbd import get_connection, ensure_tables

sql_path = Path(__file__).with_name('seed_platillos.sql')

if not sql_path.exists():
    print(f"No se encontró {sql_path}")
    raise SystemExit(1)

# Asegurarse de que las tablas existan
ensure_tables()

sql = sql_path.read_text(encoding='utf-8')

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        print("Script ejecutado.")
        cur.execute("SELECT id, nombre, precio, descripcion, creado_en FROM platillos ORDER BY id;")
        rows = cur.fetchall()
        if rows:
            print("Platillos en la tabla:")
            for r in rows:
                print(f"- {r['id']}: {r['nombre']} - ${r['precio']} - {r.get('descripcion')}")
        else:
            print("No hay platillos registrados.")
