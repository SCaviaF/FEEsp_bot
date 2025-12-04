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

# Diccionario de pilotos: APELLIDO → Nombre completo
PILOTOS = {
    "müller": "Nico Müller",
    "muller": "Nico Müller",
    "wehrlein": "Pascal Wehrlein",
    "evans": "Mitch Evans",
    "da costa": "António Félix da Costa",
    "costa": "António Félix da Costa",
    "rowland": "Oliver Rowland",
    "nato": "Norman Nato",
    "de vries": "Nyck De Vries",
    "devries": "Nyck De Vries",
    "mortara": "Edoardo Mortara",
    "günther": "Maximilian Günther",
    "gunther": "Maximilian Günther",
    "barnard": "Taylor Barnard",
    "dennis": "Jake Dennis",
    "drugovich": "Felipe Drugovich",
    "eriksson": "Joel Eriksson",
    "buemi": "Sébastien Buemi",
    "martí": "Pepe Martí",
    "marti": "Pepe Martí",
    "tictum": "Dan Ticktum",
    "tisktum": "Dan Ticktum",
    "di grassi": "Lucas di Grassi",
    "dig": "Lucas di Grassi",
    "maloney": "Zane Maloney",
    "vergne": "Jean-Éric Vergne",
    "cassidy": "Nick Cassidy",
}

# Botón inline que se añade debajo de los mensajes
SUBSCRIBE_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]]
)

# ID del grupo donde se publicarán los mensajes
GROUP_ID = os.getenv("CHANNEL_ID")

# Lista blanca de usuarios
PERSONAL_ID = int(os.getenv("PERSONAL_ID", "0"))
ALLOWED_USERS = [PERSONAL_ID]


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


# --- FUNCIÓN NUEVA: PROCESA MENSJES 'Top ...' ---
def generar_top(texto):
    # Extrae la parte después de "Top"
    lista = texto[3:].strip()

    # Separa por comas
    apellidos = [a.strip().lower() for a in lista.split(",")]

    if not (3 <= len(apellidos) <= 5):
        return None  # No válido

    nombres = []
    for ap in apellidos:
        if ap in PILOTOS:
            nombres.append(PILOTOS[ap])
        else:
            # Manejo de multi-palabra: "de vries", "da costa"
            encontrado = None
            for key in PILOTOS:
                if key.replace(" ", "") == ap.replace(" ", ""):
                    encontrado = PILOTOS[key]
                    break
            if encontrado:
                nombres.append(encontrado)
            else:
                nombres.append("Desconocido")

    # Construir mensaje Top
    medallas = ["🥇", "🥈", "🥉"]
    mensaje = f"Top {len(nombres)} actual:\n\n"

    for i, nombre in enumerate(nombres):
        if i < 3:
            mensaje += f"{medallas[i]} {nombre}\n"
        else:
            mensaje += f"{i+1}⃣ {nombre}\n"

    return mensaje.strip()


# -------- MANEJO GENERAL DE MENSAJES --------
async def format_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ No tienes permiso para usar este bot.")
        return

    text = update.message.text.strip()
    send_to_channel = True

    # Si empieza con "not", quitarlo
    if text.lower().startswith("not"):
        text = text[3:].strip()
        send_to_channel = False

    # NUEVO: detectar formato Top ...
    if text.lower().startswith("top "):
        response = generar_top(text)
        if response:
            await update.message.reply_text(
                response,
                parse_mode='Markdown',
                reply_markup=SUBSCRIBE_BUTTON
            )
            if send_to_channel:
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=response,
                    parse_mode='Markdown',
                    reply_markup=SUBSCRIBE_BUTTON
                )
            return

    # Palabras clave
    key = text.lower()
    if key in KEYWORDS:
        response = KEYWORDS[key]
    else:
        # Formato normal: negrita en el primer párrafo
        paragraphs = text.split("\n\n")
        if paragraphs:
            paragraphs[0] = f"*{paragraphs[0]}*"
        response = "\n\n".join(paragraphs)

    # Enviar siempre al usuario
    await update.message.reply_text(
        response,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        reply_markup=SUBSCRIBE_BUTTON
    )

    if send_to_channel:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=response,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=SUBSCRIBE_BUTTON
        )


# -------- MAIN --------
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, format_message))

    print("Bot corriendo...")
    app.run_polling()


if __name__ == "__main__":
    main()
