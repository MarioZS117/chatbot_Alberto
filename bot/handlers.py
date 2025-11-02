# Funciones para manejar comandos y mensajes
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes
import bot.flujos as flujos_mod
from bot.flujos import get_response
from bot.utils import guardar_usuario, log, get_usuario_id, get_platillo_id, guardar_orden, get_orden_ids_por_usuario
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import requests
import json


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto entrantes."""
    try:
        text = update.message.text if update.message else None
        user_name = update.effective_user.first_name if update.effective_user else 'Usuario'
        chat_id = update.effective_chat.id if update.effective_chat else None

        # Verificar si estamos esperando una consulta de nutrición
        expecting_nutrition = context.user_data.get('expecting_nutrition_query', False)
        if expecting_nutrition and isinstance(text, str):
            # Llamar al manejador de nutrición
            await ai_handle_nutrition(update, context)
            context.user_data.pop('expecting_nutrition_query', None)
            context.user_data.pop('selected_flow', None)
            try:
                flujos_mod.seleccion = None
            except Exception:
                setattr(flujos_mod, 'seleccion', None)
            return

        # Estado: si el usuario está en el flujo ordenar_comida esperamos datos personales
        expecting_user_data = context.user_data.get('expecting_user_data', False)
        if expecting_user_data and isinstance(text, str):
            parts = [p.strip() for p in text.split(',')]
            if len(parts) >= 3:
                nombre = parts[0]
                telefono = parts[1]
                correo = parts[2]
                # Guardamos temporalmente los datos y mostramos el menú del flujo
                context.user_data['pending_user'] = {
                    'nombre': nombre,
                    'telefono': telefono,
                    'correo': correo,
                    'chat_id': chat_id,
                }
                # Si vinimos aquí para revisar (post_review_action), la siguiente acción será ejecutar la revisión
                post_action = context.user_data.pop('post_review_action', None)
                if post_action in ('revisar_ordenes', 'revisar_citas'):
                    # resolver usuario_id (primero por chat_id, luego por nombre)
                    usuario_id = None
                    try:
                        usuario_id = get_usuario_id(chat_id)
                    except Exception:
                        usuario_id = None
                    if not usuario_id:
                        try:
                            usuario_id = get_usuario_id(nombre)
                        except Exception:
                            usuario_id = None

                    # intentar asegurar/crear el usuario si no existe
                    if not usuario_id:
                        try:
                            user_row = guardar_usuario(nombre, correo, telefono, chat_id)
                            usuario_id = user_row['id'] if user_row and 'id' in user_row else None
                        except Exception:
                            usuario_id = None

                    from bot.utils import obtener_ordenes_por_usuario, obtener_citas_por_usuario
                    if post_action == 'revisar_ordenes':
                        ordenes = obtener_ordenes_por_usuario(usuario_id)
                        if not ordenes:
                            await update.message.reply_text("No tienes órdenes registradas.")
                        else:
                            await update.message.reply_text(f"Tienes {len(ordenes)} órdenes:")
                            for o in ordenes:
                                await update.message.reply_text(f"- {o['cantidad']} x {o['platillo']} (Total: ${o['total']}) - {o['creado_en']}")
                        context.user_data.pop('expecting_user_data', None)
                        return
                    else:
                        citas = obtener_citas_por_usuario(usuario_id)
                        if not citas:
                            await update.message.reply_text("No tienes citas registradas.")
                        else:
                            await update.message.reply_text(f"Tienes {len(citas)} citas:")
                            for c in citas:
                                await update.message.reply_text(f"- {c.get('asunto','(sin asunto)')} - {c['fecha']} (creada: {c['creado_en']})")
                        context.user_data.pop('expecting_user_data', None)
                        return
                selected_flow = context.user_data.get('selected_flow')
                if selected_flow == 'ordenar_comida':
                    try:
                        flujos_mod.seleccion = 'empezar_orden'
                    except Exception:
                        setattr(flujos_mod, 'seleccion', 'empezar_orden')
                    respuestas_flow, markup_flow = get_response('', user_name)
                    for i, r in enumerate(respuestas_flow):
                        if i == len(respuestas_flow) - 1 and markup_flow:
                            await update.message.reply_text(r, reply_markup=markup_flow)
                        else:
                            await update.message.reply_text(r)
                    context.user_data['expecting_dish_selection'] = True
                elif selected_flow == 'agendar_cita':
                    try:
                        flujos_mod.seleccion = 'empezar_cita'
                    except Exception:
                        setattr(flujos_mod, 'seleccion', 'empezar_cita')
                    respuestas_flow, markup_flow = get_response('', user_name)
                    for i, r in enumerate(respuestas_flow):
                        if i == len(respuestas_flow) - 1 and markup_flow:
                            await update.message.reply_text(r, reply_markup=markup_flow)
                        else:
                            await update.message.reply_text(r)
                    # iniciar flujo de cita: pedimos fecha y hora después de los datos
                    context.user_data['expecting_cita_datetime'] = True
                else:
                    await update.message.reply_text("Gracias, tus datos han sido recibidos. Un asesor se pondrá en contacto contigo.")
                context.user_data.pop('expecting_user_data', None)
                return
            else:
                await update.message.reply_text("Formato inválido. Por favor envía tus datos en una sola línea separados por comas: Nombre, Teléfono, Correo")
                return
            
        expecting_user_selection = context.user_data.get('expecting_user_selection', False)
        if expecting_user_selection:
            await update.message.reply_text("Por favor selecciona la opción que deseas cancelar usando los botones correspondientes.")
            for i, r in enumerate(respuestas):
                await update.message.reply_text(f"{i + 1}. {r}")
            context.user_data.pop('expecting_user_selection', None)
            return

        # Si estamos esperando la cantidad para finalizar una orden
        # Si estamos esperando la fecha/hora para una cita
        expecting_cita_datetime = context.user_data.get('expecting_cita_datetime', False)
        if expecting_cita_datetime:
            # validar formato simple YYYY-MM-DD HH:MM
            try:
                fecha_text = text.strip()
                from datetime import datetime
                fecha_dt = datetime.strptime(fecha_text, "%Y-%m-%d %H:%M")
            except Exception:
                await update.message.reply_text("Formato inválido. Por favor ingresa la fecha y hora en formato YYYY-MM-DD HH:MM (ejemplo: 2025-10-12 15:30)")
                return

            pending_user = context.user_data.get('pending_user')
            if not pending_user:
                await update.message.reply_text("No encuentro tus datos personales. Por favor vuelve a ingresar: Nombre, Teléfono, Correo")
                context.user_data.pop('expecting_cita_datetime', None)
                return

            # Guardamos temporalmente la fecha y pedimos asunto
            context.user_data['pending_cita'] = {'fecha': fecha_dt}
            context.user_data.pop('expecting_cita_datetime', None)
            context.user_data['expecting_cita_asunto'] = True
            await update.message.reply_text("Fecha registrada. Por favor escribe el asunto o motivo de la cita.")
            return

        # Si estamos esperando el asunto de la cita
        expecting_cita_asunto = context.user_data.get('expecting_cita_asunto', False)
        if expecting_cita_asunto:
            asunto = text.strip() if isinstance(text, str) else ''
            pending_cita = context.user_data.pop('pending_cita', None)
            pending_user = context.user_data.pop('pending_user', None)
            context.user_data.pop('expecting_cita_asunto', None)
            if not pending_cita or not pending_user:
                await update.message.reply_text("No hay una cita pendiente. Por favor inicia el flujo nuevamente.")
                return

            # persistir usuario (si no existe) y crear cita
            try:
                user_row = guardar_usuario(pending_user['nombre'], pending_user['correo'], pending_user['telefono'], pending_user['chat_id'])
                usuario_id = user_row['id'] if user_row and 'id' in user_row else get_usuario_id(pending_user.get('chat_id') or pending_user.get('nombre'))
            except Exception as e:
                log(f"Error guardando usuario al finalizar cita: {e}", level="ERROR")
                await update.message.reply_text("Ocurrió un error al guardar tus datos. Intenta de nuevo más tarde.")
                return

            # guardar cita
            try:
                from bot.utils import guardar_cita
                guardar_cita(usuario_id, asunto, pending_cita['fecha'])
                await update.message.reply_text(f"Cita creada: {asunto} el {pending_cita['fecha'].strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                log(f"Error guardando cita: {e}", level="ERROR")
                await update.message.reply_text("Ocurrió un error al crear la cita. Intenta de nuevo más tarde.")

            # limpieza de estado del flujo
            context.user_data.pop('selected_flow', None)
            try:
                flujos_mod.seleccion = None
            except Exception:
                setattr(flujos_mod, 'seleccion', None)
            return

        # Si estamos esperando la cantidad para finalizar una orden
        expecting_quantity = context.user_data.get('expecting_quantity', False)
        if expecting_quantity:
            # validar que el usuario envió un entero
            try:
                cantidad = int(text.strip())
            except Exception:
                await update.message.reply_text("Cantidad inválida. Por favor envía un número entero.")
                return

            pending_order = context.user_data.pop('pending_order', None)
            pending_user = context.user_data.pop('pending_user', None)
            context.user_data.pop('expecting_quantity', None)
            if not pending_order or not pending_user:
                await update.message.reply_text("No se encontró una orden pendiente. Por favor inicia el flujo nuevamente.")
                return

            # persistir usuario (si no existe) y crear orden
            try:
                user_row = guardar_usuario(pending_user['nombre'], pending_user['correo'], pending_user['telefono'], pending_user['chat_id'])
                usuario_id = user_row['id'] if user_row and 'id' in user_row else get_usuario_id(pending_user.get('chat_id') or pending_user.get('nombre'))
            except Exception as e:
                log(f"Error guardando usuario al finalizar pedido: {e}", level="ERROR")
                await update.message.reply_text("Ocurrió un error al guardar tus datos. Intenta de nuevo más tarde.")
                return

            # mapear platillo y precio simple
            platillo_key = pending_order.get('platillo_key')
            platillo_name_map = {
                'ordenar_pollo': 'Pollo salteado con arroz blanco',
                'ordenar_ensalada_cesar': 'Ensalada César',
                'ordenar_sopa': 'Sopa de verduras',
            }
            price_map = {
                'ordenar_pollo': 120.0,
                'ordenar_ensalada_cesar': 80.0,
                'ordenar_sopa': 60.0,
            }
            platillo_name = platillo_name_map.get(platillo_key)
            platillo_id = get_platillo_id(platillo_name) if platillo_name else None
            total = price_map.get(platillo_key, 0.0) * cantidad

            try:
                guardar_orden(usuario_id, platillo_id, cantidad, total)
                await update.message.reply_text(f"Pedido creado: {cantidad} x {platillo_name}. Total: ${total:.2f}")
                await update.message.reply_text("Gracias por tu orden. Un asesor se pondrá en contacto contigo para confirmar los detalles.")
            except Exception as e:
                log(f"Error guardando orden: {e}", level="ERROR")
                await update.message.reply_text("Ocurrió un error al crear la orden. Intenta de nuevo más tarde.")

            # limpieza de estado del flujo
            context.user_data.pop('selected_flow', None)
            try:
                flujos_mod.seleccion = None
            except Exception:
                setattr(flujos_mod, 'seleccion', None)
            return

        respuestas, markup = get_response(text, user_name)

        for i, r in enumerate(respuestas):
            if i == len(respuestas) - 1 and markup:
                await update.message.reply_text(r, reply_markup=markup)
            else:
                await update.message.reply_text(r)

        # Si get_response solicita datos, activamos el estado correspondiente
        if any('Ingrese sus datos' in rr for rr in respuestas):
            context.user_data['expecting_user_data'] = True
        # Si get_response solicita la cantidad, activamos el flag para procesar
        if any('ingresa la cantidad' in rr.lower() for rr in respuestas):
            context.user_data['expecting_quantity'] = True

    except Exception as e:
        # Evitar que el dispatcher lance trazas sin control
        log(f"Excepción en handle_message: {e}", level="ERROR")
        try:
            await update.message.reply_text("Ocurrió un error al procesar tu mensaje. Intenta nuevamente.")
        except Exception:
            pass


async def analyze_with_ollama(food_description):
    """Analiza un platillo usando Ollama API local."""
    try:
        prompt = f"""Analiza la siguiente comida: "{food_description}"
        Proporciona un análisis nutricional detallado con el siguiente formato:
        - Calorías aproximadas
        - Macronutrientes (proteínas, carbohidratos, grasas)
        - Beneficios principales
        - Recomendaciones dietéticas
        - Posibles alergenos
        
        Responde en español y usa emojis relevantes para cada sección.
        La respuesta debe ser precisa y fácil de entender."""

        response = requests.post('http://localhost:11434/api/generate',
                               json={
                                   "model": "gemma",
                                   "prompt": prompt,
                                   "stream": False
                               })
        
        if response.status_code == 200:
            result = response.json()
            return result['response']
        else:
            return None

    except Exception as e:
        log(f"Error al llamar a Ollama: {e}", level="ERROR")
        return None

async def ai_handle_nutrition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja consultas relacionadas con calorías y nutrientes de los alimentos."""
    try:
        text = update.message.text if update.message else None
        if not text:
            await update.message.reply_text("Por favor, describe el platillo del que quieres conocer información nutricional.")
            return

        # Informar al usuario que estamos analizando
        await update.message.reply_text("🔄 Analizando tu platillo... Dame un momento.")

        # Obtener el análisis de la IA
        analysis = await analyze_with_ollama(text)
        
        if analysis:
            # Si tenemos respuesta de la IA, la usamos
            respuesta = f"🍽️ Análisis nutricional para: {text}\n\n{analysis}"
        else:
            # Respuesta de fallback si hay error
            respuesta = f"🍽️ Análisis nutricional para {text}:\n\n"
            respuesta += "🔸 Calorías: ~350-400 kcal\n"
            respuesta += "🔸 Proteínas: 25g\n"
            respuesta += "🔸 Carbohidratos: 45g\n"
            respuesta += "🔸 Grasas: 12g\n"
            respuesta += "\n⚠️ Nota: Estos son valores aproximados generados como respaldo."

        await update.message.reply_text(respuesta)
        
        # Ofrecer opciones adicionales con menú expandido
        keyboard = [
            [InlineKeyboardButton("🍽️ Ordenar este platillo", callback_data='ordenar_comida')],
            [InlineKeyboardButton("🔄 Analizar otro platillo", callback_data='ayuda_ia')],
            [InlineKeyboardButton("📋 Volver al menú principal", callback_data='menu_principal')],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "¿Qué más te gustaría hacer?",
            reply_markup=markup
        )

    except Exception as e:
        log(f"Error en ai_handle_nutrition: {e}", level="ERROR")
        await update.message.reply_text("Lo siento, hubo un error al analizar la información nutricional. Inténtalo de nuevo.")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks de botones inline."""
    try:
        pedido_id = get_orden_ids_por_usuario(update.effective_chat.id) if update.effective_chat else None
        query = update.callback_query
        await query.answer()
        data = query.data
        user_name = update.effective_user.first_name if update.effective_user else 'Usuario'

        # Si el callback es una selección de flujo, primero establecer la selección
        # en el módulo de flujos y obtener la respuesta correspondiente llamando
        # a get_response('', user_name) para que flujos.py devuelva el teclado de platillos.
        if data == 'menu_principal':
            # Limpiar el estado y mostrar el menú principal
            context.user_data.clear()
            try:
                flujos_mod.seleccion = None
            except Exception:
                setattr(flujos_mod, 'seleccion', None)
            # Simular un saludo para mostrar el menú principal
            respuestas, markup = get_response("hola", user_name)
            return await query.message.reply_text(respuestas[0], reply_markup=markup)
        elif data == 'ayuda_ia':
            context.user_data['selected_flow'] = data
            try:
                flujos_mod.seleccion = 'ayuda_ia'
            except Exception:
                setattr(flujos_mod, 'seleccion', 'ayuda_ia')
            # Activar el estado de espera para el análisis nutricional
            context.user_data['expecting_nutrition_query'] = True
            respuestas, markup = get_response(data, user_name)
        elif data in ('ordenar_comida', 'agendar_cita'):
            context.user_data['selected_flow'] = data
            try:
                flujos_mod.seleccion = data
            except Exception:
                setattr(flujos_mod, 'seleccion', data)
            # después de elegir flujo, pedimos los datos personales
            context.user_data['expecting_user_data'] = True
            respuestas, markup = get_response('', user_name)
        elif data in ('cancelar_pedido', 'cancelar_cita'):
            context.user_data['selected_flow'] = data
            try:
                flujos_mod.seleccion = data
            except Exception:
                setattr(flujos_mod, 'seleccion', data)
            
            # Manejar específicamente la cancelación de pedidos
            if data == 'cancelar_pedido':
                # Obtener usuario_id
                chat_id = query.message.chat.id if query and query.message and query.message.chat else None
                usuario_id = None
                
                if chat_id is not None:
                    try:
                        usuario_id = get_usuario_id(chat_id)
                    except Exception:
                        usuario_id = None
                
                if not usuario_id:
                    context.user_data['post_review_action'] = data
                    context.user_data['expecting_user_data'] = True
                    await query.message.reply_text("Para verificar tu identidad, por favor ingresa tus datos: Nombre, Teléfono, Correo")
                    return
                
                # Obtener órdenes activas directamente con el parámetro solo_activas
                from bot.utils import obtener_ordenes_por_usuario
                ordenes_activas = obtener_ordenes_por_usuario(usuario_id, solo_activas=True)
                
                if not ordenes_activas:
                    await query.message.reply_text("No tienes pedidos activos para cancelar.")
                    return
                
                # Mostrar órdenes activas con botones para cancelar
                await query.message.reply_text(f"📦 Tienes {len(ordenes_activas)} pedidos activos:")
                
                keyboard = []
                for orden in ordenes_activas:
                    fecha_str = orden['creado_en'].strftime('%d/%m/%Y %H:%M') if orden['creado_en'] else 'Fecha no disponible'
                    texto_boton = f"❌ {orden['cantidad']}x {orden['platillo']} - ${orden['total']} ({fecha_str})"
                    keyboard.append([InlineKeyboardButton(texto_boton, callback_data=f'cancelar_orden_{orden["id"]}')])
                
                keyboard.append([InlineKeyboardButton("🔙 Volver al menú principal", callback_data='menu_principal')])
                markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "Selecciona el pedido que deseas cancelar:", 
                    reply_markup=markup
                )
                return
            else:
                # Para cancelar_cita
                # Obtener usuario_id
                chat_id = query.message.chat.id if query and query.message and query.message.chat else None
                usuario_id = None
                
                if chat_id is not None:
                    try:
                        usuario_id = get_usuario_id(chat_id)
                    except Exception:
                        usuario_id = None
                
                if not usuario_id:
                    context.user_data['post_review_action'] = data
                    context.user_data['expecting_user_data'] = True
                    await query.message.reply_text("Para verificar tu identidad, por favor ingresa tus datos: Nombre, Teléfono, Correo")
                    return
                
                # Obtener citas activas
                from bot.utils import obtener_citas_por_usuario
                citas_activas = obtener_citas_por_usuario(usuario_id, solo_activas=True)
                
                if not citas_activas:
                    await query.message.reply_text("No tienes citas activas para cancelar.")
                    return
                
                # Mostrar citas activas con botones para cancelar
                await query.message.reply_text(f"📅 Tienes {len(citas_activas)} citas activas:")
                
                keyboard = []
                for cita in citas_activas:
                    fecha_str = cita['fecha'].strftime('%d/%m/%Y %H:%M') if cita['fecha'] else 'Fecha no disponible'
                    texto_boton = f"❌ {cita['asunto']} - {fecha_str}"
                    keyboard.append([InlineKeyboardButton(texto_boton, callback_data=f'cancelar_cita_{cita["id"]}')])
                
                keyboard.append([InlineKeyboardButton("🔙 Volver al menú principal", callback_data='menu_principal')])
                markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "Selecciona la cita que deseas cancelar:", 
                    reply_markup=markup
                )
                return
        else:
            respuestas, markup = get_response(data, user_name)

        # Si estamos esperando la selección de platillo y el callback es de platillo,
        # pedimos la cantidad y guardamos la orden pendiente en el contexto para que
        # handle_message procese la cantidad posteriormente.
        expecting_dish = context.user_data.get('expecting_dish_selection', False)
        dish_callbacks = {'ordenar_pollo', 'ordenar_ensalada_cesar', 'ordenar_sopa'}
        if expecting_dish and data in dish_callbacks:
            pending = context.user_data.get('pending_user', None)
            if not pending:
                # No hay datos personales registrados; pedir al usuario que los reingrese
                await query.message.reply_text("No encuentro tus datos personales. Por favor vuelve a ingresar: Nombre, Teléfono, Correo")
                # limpiamos flags para que vuelvan a enviar datos
                context.user_data.pop('expecting_dish_selection', None)
                context.user_data.pop('selected_flow', None)
                try:
                    flujos_mod.seleccion = None
                except Exception:
                    setattr(flujos_mod, 'seleccion', None)
                return

            # Guardamos la orden pendiente y pedimos la cantidad
            context.user_data['pending_order'] = {'platillo_key': data}
            context.user_data['expecting_quantity'] = True
            # Ya no esperamos selección de platillo
            context.user_data.pop('expecting_dish_selection', None)

            # Obtener los mensajes que flujos devuelve (deberían incluir "Por favor, ingresa la cantidad...")
            respuestas_finales, _ = get_response(data, pending.get('nombre') if pending else user_name)
            for r in respuestas_finales:
                await query.message.reply_text(r)
            # Si flujos pidió la cantidad, activamos el flag para procesarla en handle_message
            if any('ingresa la cantidad' in rr.lower() for rr in respuestas_finales):
                context.user_data['expecting_quantity'] = True
            return

        # Manejar la cancelación específica de una orden
        elif data.startswith('cancelar_orden_'):
            orden_id = data.replace('cancelar_orden_', '')
            chat_id = query.message.chat.id if query and query.message and query.message.chat else None
            usuario_id = get_usuario_id(chat_id) if chat_id else None
            
            if usuario_id:
                from bot.utils import cancelar_orden
                if cancelar_orden(orden_id, usuario_id):
                    await query.message.reply_text(f"✅ Pedido #{orden_id} cancelado exitosamente.")
                    
                    # Mostrar menú principal nuevamente
                    keyboard = [
                        [InlineKeyboardButton("Ordenar comida a domicilio.🍗", callback_data='ordenar_comida')],
                        [InlineKeyboardButton("Agendar una cita.📅", callback_data='agendar_cita')],
                        [InlineKeyboardButton("Analizar calorías y nutrientes. 🥗", callback_data='ayuda_ia')],
                        [InlineKeyboardButton("Ver mis órdenes. 📦", callback_data='revisar_ordenes')],
                        [InlineKeyboardButton("Ver mis citas. 📅", callback_data='revisar_citas')],
                        [InlineKeyboardButton("Cancelar pedido. ❌", callback_data='cancelar_pedido')],
                        [InlineKeyboardButton("Cancelar cita. ❌", callback_data='cancelar_cita')],
                    ]
                    markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("¿Qué más puedo ayudarte?", reply_markup=markup)
                else:
                    await query.message.reply_text("❌ No se pudo cancelar el pedido. Verifica que sea tuyo y esté activo.")
            else:
                await query.message.reply_text("❌ No se pudo verificar tu identidad. Intenta nuevamente.")
                
        # Manejar la cancelación específica de una cita
        elif data.startswith('cancelar_cita_'):
            cita_id = data.replace('cancelar_cita_', '')
            chat_id = query.message.chat.id if query and query.message and query.message.chat else None
            usuario_id = get_usuario_id(chat_id) if chat_id else None
            
            if usuario_id:
                from bot.utils import cancelar_cita
                if cancelar_cita(cita_id, usuario_id):
                    await query.message.reply_text(f"✅ Cita #{cita_id} cancelada exitosamente.")
                    
                    # Mostrar menú principal nuevamente
                    keyboard = [
                        [InlineKeyboardButton("Ordenar comida a domicilio.🍗", callback_data='ordenar_comida')],
                        [InlineKeyboardButton("Agendar una cita.📅", callback_data='agendar_cita')],
                        [InlineKeyboardButton("Analizar calorías y nutrientes. 🥗", callback_data='ayuda_ia')],
                        [InlineKeyboardButton("Ver mis órdenes. 📦", callback_data='revisar_ordenes')],
                        [InlineKeyboardButton("Ver mis citas. 📅", callback_data='revisar_citas')],
                        [InlineKeyboardButton("Cancelar pedido. ❌", callback_data='cancelar_pedido')],
                        [InlineKeyboardButton("Cancelar cita. ❌", callback_data='cancelar_cita')],
                    ]
                    markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text("¿Qué más puedo ayudarte?", reply_markup=markup)
                else:
                    await query.message.reply_text("❌ No se pudo cancelar la cita. Verifica que sea tuya y esté activa.")
            else:
                await query.message.reply_text("❌ No se pudo verificar tu identidad. Intenta nuevamente.")
            return
            
        # Nuevo: revisar órdenes o citas
        elif data in ('revisar_ordenes', 'revisar_citas'):
            # Intentamos resolver el usuario: preferimos chat_id (verificación por chat),
            # luego fallback a pending_user si la búsqueda por chat_id falla.
            pending = context.user_data.get('pending_user')
            chat_id = query.message.chat.id if query and query.message and query.message.chat else None
            usuario_id = None
            # Primero intentar por chat_id (verificación segura)
            if chat_id is not None:
                try:
                    usuario_id = get_usuario_id(chat_id)
                except Exception:
                    usuario_id = None
            # Si no encontramos por chat_id, intentamos con pending_user (nombre o chat almacenado)
            if not usuario_id and pending:
                try:
                    usuario_id = get_usuario_id(pending.get('chat_id') or pending.get('nombre'))
                except Exception:
                    usuario_id = None

            if not usuario_id:
                # Pedimos los datos personales para verificar identidad y luego realizamos la acción
                context.user_data['post_review_action'] = data
                context.user_data['expecting_user_data'] = True
                await query.message.reply_text("Para verificar tu identidad, por favor ingresa tus datos en una sola línea: Nombre, Teléfono, Correo")
                return

            # Importar funciones de util para obtener listas
            from bot.utils import obtener_ordenes_por_usuario, obtener_citas_por_usuario
            if data == 'revisar_ordenes':
                ordenes = obtener_ordenes_por_usuario(usuario_id)
                if not ordenes:
                    await query.message.reply_text("No tienes órdenes registradas.")
                    return
                await query.message.reply_text(f"Tienes {len(ordenes)} órdenes:")
                for o in ordenes:
                    await query.message.reply_text(f"- {o['cantidad']} x {o['platillo']} (Total: ${o['total']}) - {o['creado_en']}")
                return
            else:
                citas = obtener_citas_por_usuario(usuario_id)
                if not citas:
                    await query.message.reply_text("No tienes citas registradas.")
                    return
                await query.message.reply_text(f"Tienes {len(citas)} citas:")
                for c in citas:
                    await query.message.reply_text(f"- {c.get('asunto','(sin asunto)')} - {c['fecha']} (creada: {c['creado_en']})")
                return

        # Editar el mensaje original si es posible, si no, enviar nuevo mensaje
        if respuestas:
            try:
                if markup:
                    await query.edit_message_text(respuestas[0], reply_markup=markup)
                else:
                    await query.edit_message_text(respuestas[0])
            except Exception:
                try:
                    if markup:
                        await query.message.reply_text(respuestas[0], reply_markup=markup)
                    else:
                        await query.message.reply_text(respuestas[0])
                except Exception as e:
                    log(f"Error enviando mensaje en callback: {e}", level="ERROR")

            for r in respuestas[1:]:
                try:
                    await query.message.reply_text(r)
                except Exception:
                    log("Fallo al enviar respuesta adicional en callback", level="WARNING")

            if any('Ingrese sus datos' in rr for rr in respuestas):
                context.user_data['expecting_user_data'] = True

    except Exception as e:
        log(f"Excepción en handle_callback_query: {e}", level="ERROR")
        try:
            await update.callback_query.message.reply_text("Ocurrió un error al procesar la acción. Intenta nuevamente.")
        except Exception:
            pass
