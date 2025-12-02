import os
import re
import requests
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# TOKEN de Telegram
TOKEN = os.getenv("TOKEN")
# Bearer Token de Twitter
TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN")

# Handler /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Envíame un enlace de un tweet de Formula E y lo procesaré."
    )

# Handler para procesar tweets
async def procesar_tweet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.message.text
    match = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/[^\s]+', mensaje)

    if not match:
        await update.message.reply_text("Envíame un tweet de Formula E.")
        return

    tweet_url = match.group(0)
    tweet_id = tweet_url.split("/")[-1]

    # Llamada a la API de Twitter
    headers = {"Authorization": f"Bearer {TWITTER_BEARER}"}
    url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=attachments,entities,author_id"
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        texto = data['data']['text']

        # Obtener imagen si existe
        img_url = None
        if 'attachments' in data['data'] and 'media_keys' in data['data']['attachments']:
            # Para simplificar, solo usamos el primer media_key
            # Más avanzado: llamar al endpoint de media para obtener URLs reales
            img_url = None  # Puedes mejorar esto más adelante

    except Exception as e:
        await update.message.reply_text(f"Error al obtener el tweet: {e}")
        return

    # Traducción
    traducido = GoogleTranslator(source="auto", target="es").translate(texto)
    titulo = traducido.split(".")[0] + "."

    # Enviar imagen si existe
    if img_url:
        await update.message.reply_photo(img_url)

    # Mensaje final
    mensaje_final = f"""📢 *{titulo}*

{traducido}

Twitter FE:
🔗 {tweet_url}

🔔 *Suscríbete a mi canal para más contenido de Formula E*
"""
    await update.message.reply_text(mensaje_final, parse_mode="Markdown")

# Crear la aplicación
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_tweet))

print("Bot funcionando...")
app.run_polling()

