from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Diccionario de palabras clave y mensajes predefinidos (todo en negrita)
KEYWORDS = {
    "verde": "🟩🟩🟩🟩🟩🟩🟩\n*BANDERA VERDE*\n🟩🟩🟩🟩🟩🟩🟩",
    "amarilla": "🟨🟨🟨🟨🟨🟨🟨🟨\n*BANDERA AMARILLA*\n🟨🟨🟨🟨🟨🟨🟨🟨",
    "roja": "🟥🟥🟥🟥🟥🟥\n*BANDERA ROJA*\n🟥🟥🟥🟥🟥🟥",
    "safety": "🟨🚗🟨🚗🟨\n*SAFETY CAR*\n🟨🚗🟨🚗🟨",
    "finsafety": "🟩🚗🟩🚗🟩🚗🟩\n*FIN DEL SAFETY CAR*\n🟩🚗🟩🚗🟩🚗🟩",
    "ultima": "🔄🔄🔄🔄🔄🔄🔄\n*ÚLTIMA VUELTA!!!!*\n🔄🔄🔄🔄🔄🔄🔄",
}

# Botón inline que se añade debajo de los mensajes de palabra clave
SUBSCRIBE_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]]
)

# ID o username del grupo donde se publicarán los mensajes
GROUP_ID = os.getenv("CHANNEL_ID")  # valor por defecto opcional

# Lista blanca de usuarios (solo ellos pueden usar el bot)
PERSONAL_ID = int(os.getenv("PERSONAL_ID", "0"))  # 0 por defecto si no existe
ALLOWED_USERS = [PERSONAL_ID]  # Reemplaza con tu ID real

# Función de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return

    await update.message.reply_text(
        "¡Hola! Envíame un mensaje y pondré en negrita el primer párrafo.\n"
        "Claves: verde, amarilla, roja, safety, finsafety, ultima.",
        disable_web_page_preview=True
    )

# Función para procesar mensajes con whitelist y lógica "not"
async def format_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return

    text = update.message.text.strip()
    send_to_channel = True  # Por defecto, se envía al canal

    # Si empieza con "not", quitar "not" y no enviar al canal
    if text.lower().startswith("not"):
        text = text[3:].strip()  # Quitar "not" y espacios
        send_to_channel = False

    # Verificar si es palabra clave
    key = text.lower()
    if key in KEYWORDS:
        response = KEYWORDS[key]
    else:
        # Formateo normal: negrita en el primer párrafo
        paragraphs = text.split('\n\n')
        if paragraphs:
            paragraphs[0] = f"*{paragraphs[0]}*"
        response = '\n\n'.join(paragraphs)

    # Enviar siempre al usuario
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=SUBSCRIBE_BUTTON
    )

    # Enviar al grupo solo si no empieza con "not"
    if send_to_channel:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=response,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=SUBSCRIBE_BUTTON
        )

# Función principal
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, format_message))

    print("Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()

