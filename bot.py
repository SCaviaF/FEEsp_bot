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
GROUP_ID = "@GPdeMadrid"  # Si tu grupo tiene username, usa "@GPdeMadrid"

# Función de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un mensaje y pondré en negrita el primer párrafo.\n"
        "Claves: verde, amarilla, roja, safety, finsafety, ultima.",
        disable_web_page_preview=True
    )

# Función para procesar mensajes
async def format_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    
    if text in KEYWORDS:
        # Mensaje de palabra clave con negrita y botón
        response = KEYWORDS[text]
        # Enviar al usuario
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=SUBSCRIBE_BUTTON
        )
        # Enviar al grupo
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=response,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=SUBSCRIBE_BUTTON
        )
    else:
        # Formateo normal: negrita en el primer párrafo
        paragraphs = update.message.text.split('\n\n')
        if paragraphs:
            paragraphs[0] = f"*{paragraphs[0]}*"
        formatted_text = '\n\n'.join(paragraphs)
        # Enviar al usuario
        await update.message.reply_text(
            formatted_text,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=SUBSCRIBE_BUTTON
        )
        # Enviar al grupo
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=formatted_text,
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
