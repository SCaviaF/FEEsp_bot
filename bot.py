from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os

FOOTER_MESSAGE = "\n\nSuscríbete en: t.me/FormulaEEsp"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un mensaje y pondré en negrita el primer párrafo y añadiré un enlace al final."
    )

async def format_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    paragraphs = text.split('\n\n')
    if paragraphs:
        paragraphs[0] = f"*{paragraphs[0]}*"
    formatted_text = '\n\n'.join(paragraphs) + FOOTER_MESSAGE
    await update.message.reply_text(formatted_text, parse_mode='Markdown')

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")  # Lo tomamos de las variables de entorno
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, format_message))

    print("Bot corriendo...")
    app.run_polling()

if __name__ == "__main__":
    main()
