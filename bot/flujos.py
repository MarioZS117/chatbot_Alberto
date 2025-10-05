import random
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import re  # Se importa la librería para expresiones regulares
# from bot.utils import guardar_usuario, guardar_datos, get_precio_producto, guardar_cotizacion
import threading
# flujos solo construye mensajes y botones; la persistencia la maneja handlers


# selección de flujo actual (se establece por handlers cuando el usuario elige una opción)
seleccion = None

# --- Listas de Opciones ---
saludos = ["hola", "hols", "ola", "hoa", "hla", "que hay", "aloooh", "holiwis", "que onda", "ayuda"]
respuestas_saludos = [
    "¡Hola! espero que estés bien. Te doy la bienvenida a NutriLogic. Te ayudamos con tu nutrición.",
    "¡Hey! ¿Qué tal? Estás en NutriLogic, el hogar de la nutrición.",
    "¡Saludos!. Te presento a NutriLogic, en donde te ayudamos con tu alimentación.",
]


def get_response(text, user_name):
    """Devuelve (respuestas:list[str], markup:InlineKeyboardMarkup|None).

    Siempre garantiza que se retorne una tupla. Maneja saludos, comandos básicos,
    selección de flujo (ordenar_comida/agendar_cita) y el parseo simple de datos "Nombre, Teléfono, Correo".
    """
    global seleccion

    if not isinstance(text, str):
        return ["Entrada inválida."], None

    text = text.strip()
    lower = text.lower()
    respuestas = []
    markup = None

    # teclado común
    keyboard = [
        [InlineKeyboardButton("Ordenar comida a domicilio.", callback_data='ordenar_comida')],
        [InlineKeyboardButton("Agendar una cita.", callback_data='agendar_cita')],
    ]

    # saludos
    if lower in saludos:
        respuestas.append(random.choice(respuestas_saludos))
        respuestas.append("¿Dime, que es lo que necesitas?")
        markup = InlineKeyboardMarkup(keyboard)
        seleccion = text
        return respuestas, markup

    # comandos
    if lower == "/start":
        respuestas.append(f"Hola {user_name}, bienvenido al bot de TecnoStore.")
        return respuestas, None
    if lower == "/help":
        respuestas.append("¡Hola! Soy el asistente virtual de TecnoStore. Puedes saludarme con 'hola'.")
        return respuestas, None

    # callbacks (cuando el usuario selecciona una opción)
    # Consideramos dos fuentes: el texto actual (lower) o la variable de módulo `seleccion`
    if (lower in ("ordenar_comida", "agendar_cita")) or (not lower and seleccion in ("ordenar_comida", "agendar_cita")):
        respuestas.append("Ingrese sus datos en el siguiente formato: Nombre, Teléfono, Correo")
        respuestas.append("Ejemplo: Juan Perez, 555-1234, juanperez@example.com")
        # devolvemos el teclado por conveniencia
        source = lower if lower in ("ordenar_comida", "agendar_cita") else seleccion
        if source == "ordenar_comida":
            seleccion = "empezar_orden"
        elif source == "agendar_cita":
            seleccion = "empezar_cita"
        markup = InlineKeyboardMarkup(keyboard)
        return respuestas, markup

    # Si viene una línea con formato "Nombre, Teléfono, Correo" intentamos parsear y guardar
    if text.count(",") >= 2:
        # Cuando el usuario envía "Nombre, Teléfono, Correo" flujos solo responde
        # para confirmar recepción; el handler del bot es responsable de guardar los datos.
        partes = [p.strip() for p in text.split(",", 2)]
        nombre = partes[0]
        respuestas.append("Gracias, tus datos han sido recibidos. Ahora selecciona el platillo que deseas ordenar.")
        return respuestas, None
    if seleccion == "empezar_orden":
        respuestas.append("¡Perfecto! Vamos a ordenar tu comida.")
        respuestas.append("Por favor, selecciona el platillo a ordenar.")
        keyboard = [
            [InlineKeyboardButton("Pollo salteado con arroz blanco", callback_data='ordenar_pollo')],
            [InlineKeyboardButton("Ensalada César", callback_data='ordenar_ensalada_cesar')],
            [InlineKeyboardButton("Sopa de verduras", callback_data='ordenar_sopa')],
        ]
        # Si se ha enviado el callback del platillo, pedimos la cantidad; si no, mostramos el teclado
        if lower in ("ordenar_pollo", "ordenar_ensalada_cesar", "ordenar_sopa"):
            if lower == "ordenar_pollo":
                respuestas.append("Has seleccionado Pollo salteado con arroz blanco.")
            elif lower == "ordenar_ensalada_cesar":
                respuestas.append("Has seleccionado Ensalada César.")
            elif lower == "ordenar_sopa":
                respuestas.append("Has seleccionado Sopa de verduras.")
            # Pedimos la cantidad al usuario; la creación de la orden la hará el handler
            respuestas.append("Por favor, ingresa la cantidad que deseas (número entero).")
            return respuestas, None
        else:
            # mostrar teclado para seleccionar platillo
            return respuestas, InlineKeyboardMarkup(keyboard)
    # fallback
    respuestas.append("No entendí tu mensaje. Puedes escribir 'hola' o usar los botones.")
    markup = InlineKeyboardMarkup(keyboard)
    return respuestas, markup