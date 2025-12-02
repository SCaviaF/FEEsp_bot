from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

FOOTER_MESSAGE = "\n\nSuscríbete en: t.me/FormulaEEsp"

# Diccionario de palabras clave y mensajes predefinidos
KEYWORDS = {
    "verde": "🟩🟩🟩🟩🟩🟩🟩\nBANDERA VERDE\n🟩🟩🟩🟩🟩🟩🟩",
    "amarilla": "🟨🟨🟨🟨🟨🟨🟨🟨\nBANDERA AMARILLA\n🟨🟨🟨🟨🟨🟨🟨🟨",
    "roja": "🟥🟥🟥🟥🟥🟥\nBANDERA ROJA\n🟥🟥🟥🟥🟥🟥",
    "safety": "🟨🚗🟨🚗🟨\nSAFETY CAR\n🟨🚗🟨🚗🟨",
    "finsafety": "🟩🚗🟩🚗🟩🚗🟩\nFIN DEL SAFETY CAR\n🟩🚗🟩🚗🟩🚗🟩",
    "ultima": "🔄🔄🔄🔄🔄🔄🔄\nÚLTIMA VUELTA!!!!",
    # Agrega más palabras aquí hasta 10
}
# Función de inicio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un mensaje y pondré en negrita el primer párrafo y añadiré un enlace al final.\n"
        "Si envías una palabra clave, te devolveré un mensaje especial."
    )

# Función para procesar mensajes
async def format_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()  # Convertimos a minúsculas para coincidencias
    if text in KEYWORDS:
        # Si la palabra coincide con el diccionario
        response = KEYWORDS[text] + FOOTER_MESSAGE
        await update.message.reply_text(response)
    else:
        # Formateo normal: negrita en el primer párrafo + mensaje al final
        paragraphs = update.message.text.split('\n\n')
        if paragraphs:
            paragraphs[0] = f"*{paragraphs[0]}*"
        formatted_text = '\n\n'.join(paragraphs) + FOOTER_MESSAGE
        await update.message.reply_text(formatted_text, parse_mode='Markdown')

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
