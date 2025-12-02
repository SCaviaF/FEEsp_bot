import re
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

translator = Translator()

async def procesar_tweet(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = update.message.text
    match = re.search(r'https?://(?:www\.)?(?:x|twitter)\.com/[^\s]+', mensaje)

    if not match:
        await update.message.reply_text("Envíame un tweet de Formula E.")
        return

    tweet_url = match.group(0)
    # Convertimos la URL a Nitter
    nitter_url = tweet_url.replace("twitter.com", "nitter.net").replace("x.com", "nitter.net")

    # Scraping desde Nitter
    r = requests.get(nitter_url)
    soup = BeautifulSoup(r.text, "html.parser")

    # Texto del tweet
    texto = soup.find('div', class_='tweet-content').get_text(strip=True)

    # Imagen del tweet
    img_tag = soup.find('a', class_='still-image')
    img_url = None
    if img_tag:
        img_url = "https://nitter.net" + img_tag['href']

    # Traducción
    traducido = translator.translate(texto, dest="es").text

    # Crear título (simple resumen)
    titulo = traducido.split(".")[0] + "."

    # Enviar imagen si existe
    if img_url:
        await update.message.reply_photo(img_url)

    # Mensaje final
    mensaje_final = f"""
📢 *{titulo}*

{traducido}

Twitter FE:
🔗 {tweet_url}

🔔 *Suscríbete a mi canal para más contenido de Formula E*
"""

    await update.message.reply_text(mensaje_final, parse_mode="Markdown")

async def main():
    TOKEN = "AQUÍ_TU_TOKEN_DE_TELEGRAM"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_tweet))

    print("Bot funcionando...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
