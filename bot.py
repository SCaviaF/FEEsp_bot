import os
import re
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)

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
    nitter_url = tweet_url.replace("twitter.com", "nitter.net").replace("x.com", "nitter.net")

    # Scraping desde Nitter
    r = requests.get(nitter_url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Texto del tweet (versión robusta)
    texto_tag = soup.find('div', class_='tweet-content')
    if texto_tag:
        # Primero intenta extraer el <p> dentro del div
        p = texto_tag.find('p')
        if p:
            texto = p.get_text(strip=True)
        else:
            # Si no hay <p>, toma todo el texto del div
            texto = texto_tag.get_text(strip=True)
    else:
        await update.message.reply_text("No pude obtener el texto del tweet.")
        return

    # Imagen del tweet
    img_tag = soup.find('a', class_='still-image')
    img_url = None
    if img_tag:
        img_url = "https://nitter.net" + img_tag['href']

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






