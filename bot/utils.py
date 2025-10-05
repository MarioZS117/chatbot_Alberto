#Manejar los mensajes, aqui podríamos usar BD o que se yo
# Manejar los mensajes, aqui podríamos usar BD o que se yo

import datetime
from fpdf import FPDF
from bot.model.neonbd import get_connection, ensure_tables


def log(message, level="INFO"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{level}] {now} - {message}")


def validate_text(text):
    if not text or not isinstance(text, str):
        return False
    return True


def safe_get(d, path, default=None):
    """
    Accede a claves anidadas de un diccionario sin explotar.
    Ejemplo: safe_get(update, ["message","chat","id"])
    """
    for key in path:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d


def guardar_usuario(nombre, correo, telefono, chat_id):
    """Guarda un usuario en la tabla `usuarios`.

    Crea la tabla si no existe y luego inserta el registro.
    """
    ensure_tables()
    insert_sql = """
    INSERT INTO usuarios (nombre, correo, telefono, chat_id)
    VALUES (%s, %s, %s, %s)
    RETURNING id, creado_en
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(insert_sql, (nombre, correo, telefono, chat_id))
            row = cur.fetchone()
            return row
def guardar_orden(usuario_id, platillo_id, cantidad, total, creado_en=datetime.datetime.now()):
    """Guarda una orden en la tabla `ordenes`.

    Crea la tabla si no existe y luego inserta el registro.
    """
    ensure_tables()
    insert_sql = """
    INSERT INTO ordenes (usuario_id, platillo_id, cantidad, total, creado_en)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, creado_en
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(insert_sql, (usuario_id, platillo_id, cantidad, total, creado_en))
            row = cur.fetchone()
            return row
        
def get_usuario_id(chat_id):
    """Obtiene el ID del usuario dado su chat_id."""
    if chat_id is None:
        return None

    # Si chat_id es numérico (int o cadena de dígitos), lo consultamos por chat_id (BIGINT).
    # Si no, lo interpretamos como nombre y consultamos por nombre.
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # intentar convertir a entero
                cid = int(chat_id)
                query_sql = "SELECT id FROM usuarios WHERE chat_id = %s"
                cur.execute(query_sql, (cid,))
            except Exception:
                query_sql = "SELECT id FROM usuarios WHERE nombre = %s"
                cur.execute(query_sql, (chat_id,))
            row = cur.fetchone()
            return row['id'] if row else None

def get_platillo_id(nombre):
    """Obtiene el ID del platillo dado su nombre."""
    query_sql = "SELECT id FROM platillos WHERE nombre = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query_sql, (nombre,))
            row = cur.fetchone()
            return row['id'] if row else None