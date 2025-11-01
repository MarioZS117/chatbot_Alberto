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
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Si nos dieron chat_id, comprobar si ya existe un usuario con ese chat_id
            if chat_id is not None:
                try:
                    cur.execute("SELECT id, nombre, correo, telefono, chat_id, creado_en FROM usuarios WHERE chat_id = %s", (chat_id,))
                    existing = cur.fetchone()
                    if existing:
                        # devolver el usuario existente (se considera 'login')
                        return existing
                except Exception:
                    # continuar al insert si algo falla en la comprobación
                    pass

            insert_sql = """
            INSERT INTO usuarios (nombre, correo, telefono, chat_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, nombre, correo, telefono, chat_id, creado_en
            """
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


def obtener_ordenes_por_usuario(usuario_id):
    """Devuelve una lista de órdenes (con datos de platillo) para el usuario dado.

    Cada elemento es un dict con keys: id, platillo, cantidad, total, creado_en
    """
    if usuario_id is None:
        return []
    sql = """
    SELECT o.id, COALESCE(p.nombre, '') AS platillo, o.cantidad, o.total, o.creado_en
    FROM ordenes o
    LEFT JOIN platillos p ON o.platillo_id = p.id
    WHERE o.usuario_id = %s
    ORDER BY o.creado_en DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (usuario_id,))
            rows = cur.fetchall()
            return rows or []


def obtener_citas_por_usuario(usuario_id):
    """Devuelve una lista de citas para el usuario dado.

    Cada elemento contiene: id, asunto, fecha, creado_en
    """
    if usuario_id is None:
        return []
    sql = """
    SELECT id, asunto, fecha, creado_en
    FROM citas
    WHERE usuario_id = %s
    ORDER BY fecha DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (usuario_id,))
            rows = cur.fetchall()
            return rows or []


def guardar_cita(usuario_id, asunto, fecha, creado_en=datetime.datetime.now()):
    """Guarda una cita en la tabla `citas`.

    Es idempotente respecto a la creación de las tablas; retorna la fila insertada.
    """
    ensure_tables()
    insert_sql = """
    INSERT INTO citas (usuario_id, fecha, creado_en)
    VALUES (%s, %s, %s)
    RETURNING id, creado_en
    """
    # nota: guardamos el asunto en una columna aparte si quieres guardarlo,
    # el esquema solicitado fue (usuario_id, asunto, fecha, creado_en).
    # Si la tabla citas no contiene la columna asunto, la añadiremos usando la siguiente variante:
    with get_connection() as conn:
        with conn.cursor() as cur:
            # comprobar si existe la columna 'asunto'
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='citas' AND column_name='asunto'")
            col = cur.fetchone()
            if not col:
                try:
                    cur.execute("ALTER TABLE citas ADD COLUMN asunto TEXT")
                except Exception:
                    # si falla por permisos u otra razón, seguimos intentando insertar sin asunto
                    pass
            # ahora insertamos
            try:
                cur.execute("INSERT INTO citas (usuario_id, asunto, fecha, creado_en) VALUES (%s, %s, %s, %s) RETURNING id, creado_en", (usuario_id, asunto, fecha, creado_en))
            except Exception:
                # fallback: si por alguna razón la columna asunto no existe, intentamos insertar sin ella
                cur.execute(insert_sql, (usuario_id, fecha, creado_en))
            row = cur.fetchone()
            return row