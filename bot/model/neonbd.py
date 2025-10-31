"""Helpers para conectarse a la base de datos Neon (Postgres).

Provee un context manager `get_connection()` que devuelve una conexión
psycopg2 y permite usar `with get_connection() as conn:`.
La URL provista por el usuario se usa directamente aquí.
"""
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
import os

# URL de conexión provista (Neon Postgres). Puedes moverla a bot/config.py si prefieres.
NEON_DATABASE_URL = (
    'postgresql://neondb_owner:npg_4OstDWqC5niL@ep-fancy-bonus-adk7haoq-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
)


@contextmanager
def get_connection():
	"""Context manager que devuelve una conexión psycopg2.

	Uso:
		with get_connection() as conn:
			with conn.cursor() as cur:
				cur.execute("SELECT 1")

	La conexión usa autocommit=False; se hace commit al salir si no hubo excepción,
	de lo contrario se hace rollback.
	"""
	conn = None
	try:
		conn = psycopg2.connect(NEON_DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
		conn.autocommit = False
		yield conn
		conn.commit()
	except Exception:
		if conn:
			conn.rollback()
		raise
	finally:
		if conn:
			conn.close()


def ensure_tables():
    """Asegura que las tablas necesarias existan en la base de datos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Tabla de usuarios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    correo TEXT,
                    telefono TEXT,
                    chat_id BIGINT,
                    creado_en TIMESTAMP DEFAULT NOW()
                )
            """)
            # Tabla de platillos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS platillos (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    descripcion TEXT,
                    precio DECIMAL(10,2)
                )
            """)
            # Tabla de órdenes (añadir campo estado)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ordenes (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id),
                    platillo_id INTEGER REFERENCES platillos(id),
                    cantidad INTEGER NOT NULL,
                    total DECIMAL(10,2) NOT NULL,
                    creado_en TIMESTAMP DEFAULT NOW(),
                    estado TEXT DEFAULT 'activa'
                )
            """)
            # Tabla de citas (añadir campo estado)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS citas (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER REFERENCES usuarios(id),
                    asunto TEXT,
                    fecha TIMESTAMP NOT NULL,
                    creado_en TIMESTAMP DEFAULT NOW(),
                    estado TEXT DEFAULT 'activa'
                )
            """)
            # Insertar platillos si no existen
            cur.execute("SELECT COUNT(*) FROM platillos")
            count = cur.fetchone()['count']
            if count == 0:
                cur.execute("INSERT INTO platillos (nombre, descripcion, precio) VALUES (%s, %s, %s)", 
                            ('Pollo salteado con arroz blanco', 'Delicioso pollo salteado con vegetales y arroz blanco', 120.0))
                cur.execute("INSERT INTO platillos (nombre, descripcion, precio) VALUES (%s, %s, %s)", 
                            ('Ensalada César', 'Ensalada fresca con aderezo César y pollo a la parrilla', 80.0))
                cur.execute("INSERT INTO platillos (nombre, descripcion, precio) VALUES (%s, %s, %s)", 
                            ('Sopa de verduras', 'Sopa caliente de verduras de la temporada', 60.0))

