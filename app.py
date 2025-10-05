#Pagina principal   usar   python app.py

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot.config import BOT_TOKEN
from bot.handlers import handle_message, handle_callback_query
from telegram.ext import CallbackQueryHandler
from bot.model import neonbd  # Asegura que las tablas estén creadas al iniciar

app = ApplicationBuilder().token(BOT_TOKEN).build()

# Comando /start
async def start(update, context):
    await update.message.reply_text(f"Hola {update.effective_user.first_name}, bienvenido al bot!")

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback_query))

neonbd.ensure_tables()

print("Bot en ejecución...")
app.run_polling()