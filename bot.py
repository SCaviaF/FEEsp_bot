import os
import re
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)
import snscrape.modules.twitter as sntwitter

# TOKEN desde variables de entorno
TOKEN = os.getenv("TOKEN")

# Handler para /start
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

    # Obtener texto e imagen del tweet con snscrape
    try:
        tweet = next(sntwitter.TwitterTweetScraper(tweet_id).get_items())
        texto = tweet.content
        # Obtener la primera imagen si existe
        img_url = None
        if tweet.media:
            for m in tweet.media:
                if hasattr(m, 'fullUrl'):
                    img_url = m.fullUrl
                    break
    except StopIteration:
        await update.message.reply_text("No pude obtener el texto del tweet.")
        return
    except Exception as e:
        await update.message.reply_text(f"Error al obtener el tweet: {e}")
        return

    # Traducción
    traducido = GoogleTranslator(source="auto", target="es").translate(texto)

    # Título simple
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

# Agregar handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_tweet))

# Ejecutar el bot
print("Bot funcionando...")
app.run_polling()

