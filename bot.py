import re
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

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
    traducido = GoogleTranslator(source="auto", target="es").translate(texto)

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

app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_tweet))

try:
    print("Bot funcionando...")
    app.run_polling()
except Exception as e:
    print("Error en el bot:", e)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())




