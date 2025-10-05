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
	"postgresql://neondb_owner:npg_4OstDWqC5niL@ep-fancy-bonus-adk7haoq-pooler.c-2.us-east-1.aws.neon.tech/neondb"
	"?sslmode=require&channel_binding=require"
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
    """Crea tablas mínimas necesarias si no existen.

    Actualmente crea la tabla `usuarios` usada por `guardar_usuario`.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        correo TEXT,
        telefono TEXT,
        chat_id BIGINT,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS platillos (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        precio NUMERIC(10, 2) NOT NULL,
        descripcion TEXT,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS ordenes (
        id SERIAL PRIMARY KEY,
        usuario_id INT REFERENCES usuarios(id),
        platillo_id INT REFERENCES platillos(id),
        cantidad INT NOT NULL,
        total NUMERIC(10, 2) NOT NULL,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
	CREATE TABLE IF NOT EXISTS citas (
        id SERIAL PRIMARY KEY,
        usuario_id INT REFERENCES usuarios(id),
        fecha TIMESTAMP WITH TIME ZONE NOT NULL,
        creado_en TIMESTAMP WITH TIME ZONE DEFAULT now()
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
    print("Tablas creadas.")

