from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Variable global para controlar el flujo
seleccion = None

def get_response(text: str, user_name: str) -> tuple[list[str], InlineKeyboardMarkup | None]:
    global seleccion

    # Si el usuario envía "hola" o inicia el chat, mostramos el menú principal
    if text.lower() in ['hola', 'hi', 'hello', 'inicio', 'start', 'menu']:
        seleccion = None
        # Menú principal con opciones ampliadas
        keyboard = [
            [InlineKeyboardButton("🍽️ Ordenar comida", callback_data='ordenar_comida')],
            [InlineKeyboardButton("📅 Agendar cita", callback_data='agendar_cita')],
            [InlineKeyboardButton("🤖 Consultar nutrición (IA)", callback_data='ayuda_ia')],
            [InlineKeyboardButton("📋 Revisar órdenes", callback_data='revisar_ordenes')],
            [InlineKeyboardButton("📋 Revisar citas", callback_data='revisar_citas')],
            [InlineKeyboardButton("❌ Cancelar orden", callback_data='cancelar_orden')],
            [InlineKeyboardButton("❌ Cancelar cita", callback_data='cancelar_cita')],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        return [f"¡Hola {user_name}! Soy tu asistente virtual. ¿En qué puedo ayudarte?"], markup

    # Si el usuario elige una opción del menú, manejamos según la selección
    if seleccion is None:
        # Si no hay selección, mostramos el menú principal
        keyboard = [
            [InlineKeyboardButton("🍽️ Ordenar comida", callback_data='ordenar_comida')],
            [InlineKeyboardButton("📅 Agendar cita", callback_data='agendar_cita')],
            [InlineKeyboardButton("🤖 Consultar nutrición (IA)", callback_data='ayuda_ia')],
            [InlineKeyboardButton("📋 Revisar órdenes", callback_data='revisar_ordenes')],
            [InlineKeyboardButton("📋 Revisar citas", callback_data='revisar_citas')],
            [InlineKeyboardButton("❌ Cancelar orden", callback_data='cancelar_orden')],
            [InlineKeyboardButton("❌ Cancelar cita", callback_data='cancelar_cita')],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        return [f"¡Hola {user_name}! Soy tu asistente virtual. ¿En qué puedo ayudarte?"], markup

    # Flujo para ordenar comida
    if seleccion == 'ordenar_comida':
        # Submenú de platillos
        keyboard = [
            [InlineKeyboardButton("🍗 Pollo salteado con arroz blanco", callback_data='ordenar_pollo')],
            [InlineKeyboardButton("🥗 Ensalada César", callback_data='ordenar_ensalada_cesar')],
            [InlineKeyboardButton("🍲 Sopa de verduras", callback_data='ordenar_sopa')],
            [InlineKeyboardButton("🔙 Volver al menú principal", callback_data='menu_principal')],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        return [f"{user_name}, has seleccionado ordenar comida. Por favor elige un platillo:"], markup

    # Flujo para agendar cita
    if seleccion == 'agendar_cita':
        # Pedir fecha y hora
        return [f"{user_name}, para agendar una cita, primero necesito que ingreses tus datos personales en el formato: Nombre, Teléfono, Correo", "Por ejemplo: Juan Pérez, 123456789, juan@example.com"], None

    # Flujo para consultar nutrición
    if seleccion == 'ayuda_ia':
        return [f"{user_name}, puedes contarme sobre el platillo del cual quieres conocer información nutricional. Descríbelo brevemente."], None

    # Flujo para platillos específicos
    if seleccion in ['ordenar_pollo', 'ordenar_ensalada_cesar', 'ordenar_sopa']:
        # Mapear nombres de platillos
        platillo_map = {
            'ordenar_pollo': 'Pollo salteado con arroz blanco',
            'ordenar_ensalada_cesar': 'Ensalada César',
            'ordenar_sopa': 'Sopa de verduras'
        }
        platillo = platillo_map.get(seleccion, 'platillo')
        # Pedir la cantidad
        return [f"Has seleccionado {platillo}. Por favor, ingresa la cantidad que deseas ordenar (solo el número):"], None

    # Flujo para empezar orden (después de ingresar datos personales)
    if seleccion == 'empezar_orden':
        # Submenú de platillos
        keyboard = [
            [InlineKeyboardButton("🍗 Pollo salteado con arroz blanco", callback_data='ordenar_pollo')],
            [InlineKeyboardButton("🥗 Ensalada César", callback_data='ordenar_ensalada_cesar')],
            [InlineKeyboardButton("🍲 Sopa de verduras", callback_data='ordenar_sopa')],
            [InlineKeyboardButton("🔙 Volver al menú principal", callback_data='menu_principal')],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        return [f"Perfecto {user_name}, ahora elige el platillo que deseas ordenar:"], markup

    # Flujo para empezar cita (después de ingresar datos personales)
    if seleccion == 'empezar_cita':
        return [f"Excelente {user_name}, ahora necesito que ingreses la fecha y hora para tu cita en el formato: YYYY-MM-DD HH:MM", "Por ejemplo: 2025-10-12 15:30"], None

    # Si no se reconoce el flujo, volver al menú principal
    seleccion = None
    keyboard = [
        [InlineKeyboardButton("🍽️ Ordenar comida", callback_data='ordenar_comida')],
        [InlineKeyboardButton("📅 Agendar cita", callback_data='agendar_cita')],
        [InlineKeyboardButton("🤖 Consultar nutrición (IA)", callback_data='ayuda_ia')],
        [InlineKeyboardButton("📋 Revisar órdenes", callback_data='revisar_ordenes')],
        [InlineKeyboardButton("📋 Revisar citas", callback_data='revisar_citas')],
        [InlineKeyboardButton("❌ Cancelar orden", callback_data='cancelar_orden')],
        [InlineKeyboardButton("❌ Cancelar cita", callback_data='cancelar_cita')],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    return [f"¡Hola {user_name}! Soy tu asistente virtual. ¿En qué puedo ayudarte?"], markup