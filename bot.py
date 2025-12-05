import os
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ==========================
#   VARIABLES DE ENTORNO
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID"))
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL")  # Ejemplo: "@FormulaEEsp"

# ==========================
#   SESIÓN DE USUARIO
# ==========================
user_state = {}  # Memoria temporal por usuario (imagen/video + texto + pasos)


# ==========================
#   CHECK DE PERMISOS
# ==========================
def allowed(update: Update):
    """Devuelve True si el usuario es el autorizado."""
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID


# ==========================
#   RECEPCIÓN DE MEDIA
# ==========================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allowed(update):
        return

    message = update.message

    # Imagen
    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
    # Vídeo
    elif message.video:
        file_id = message.video.file_id
        media_type = "video"
    else:
        await message.reply_text("Envíame una imagen o un vídeo con el texto.")
        return

    if not message.caption:
        await message.reply_text("Incluye un texto en el mensaje con la imagen o video.")
        return

    user_id = update.effective_user.id

    # Guardamos el estado inicial
    user_state[user_id] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": message.caption,
        "category": None,
        "source": None,
        "schedule": None
    }

    # Preguntar categoría
    keyboard = [
        [
            InlineKeyboardButton("Noticia", callback_data="cat_Noticia"),
            InlineKeyboardButton("Estadísticas", callback_data="cat_Estadísticas"),
        ],
        [
            InlineKeyboardButton("Manual", callback_data="cat_Manual"),
            InlineKeyboardButton("Resultados", callback_data="cat_Resultados"),
        ],
        [InlineKeyboardButton("Otros", callback_data="cat_Otros")]
    ]

    await message.reply_text("¿Qué tipo de contenido es?", reply_markup=InlineKeyboardMarkup(keyboard))


# ==========================
#   CALLBACK DE BOTONES
# ==========================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if not state:
        await query.edit_message_text("No hay sesión activa. Envíame otra imagen o vídeo.")
        return

    data = query.data

    # Elegir categoría
    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        state["category"] = category

        await query.edit_message_text(
            f"Categoría seleccionada: {category}\n\nEscribe ahora el nombre de la **fuente**."
        )
        return

    # Elegir envío ahora o programar
    if data.startswith("send_"):
        action = data.replace("send_", "")

        if action == "now":
            await send_post(update, context, scheduled=False)
        else:
            state["schedule"] = True
            await query.edit_message_text(
                "Mensaje programado para +2 minutos."
            )
            await schedule_post(context, user_id)

        return


# ==========================
#   MANEJAR TEXTO COMO “FUENTE”
# ==========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)

    # Solo se interpreta como fuente si estamos en ese paso
    if state and state["category"] and state["source"] is None:
        state["source"] = update.message.text

        # Preguntar si enviar ahora o programar
        keyboard = [
            [
                InlineKeyboardButton("Enviar ahora", callback_data="send_now"),
                InlineKeyboardButton("Programar", callback_data="send_later"),
            ]
        ]

        await update.message.reply_text(
            f"Fuente guardada: {state['source']}\n\n¿Enviar ahora o programar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


# ==========================
#   FORMATEO DEL TEXTO
# ==========================
def format_caption(original_text, category, source):
    paragraphs = original_text.strip().split("\n")
    first_bold = f"*{paragraphs[0]}*"
    rest = "\n".join(paragraphs[1:])

    final_text = first_bold
    if rest:
        final_text += "\n" + rest

    # Hashtag
    hashtags = {
        "Noticia": "#Noticia",
        "Estadísticas": "#Estadísticas",
        "Manual": "#ManualFE",
        "Resultados": "#Resultados",
        "Otros": ""
    }

    tag = hashtags.get(category, "")
    if tag:
        final_text += f"\n\n{tag}"

    # Añadir enlace si lo hay
    link = ""
    for word in original_text.split():
        if word.startswith("http://") or word.startswith("https://"):
            link = word

    if link:
        final_text += f"\n🔗 [{source}]({link})"

    return final_text


# ==========================
#   ENVÍO DEL POST
# ==========================
async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE, scheduled=False):
    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if not state:
        return

    formatted = format_caption(state["caption"], state["category"], state["source"])

    # Botón SUSCRÍBETE
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]
    ])

    if state["media_type"] == "photo":
        await context.bot.send_photo(
            chat_id=TARGET_CHANNEL,
            photo=state["file_id"],
            caption=formatted,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await context.bot.send_video(
            chat_id=TARGET_CHANNEL,
            video=state["file_id"],
            caption=formatted,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # Confirmación solo al usuario
    if not scheduled:
        await update.callback_query.edit_message_text("✔ Publicado en el canal.")

    user_state.pop(user_id, None)


# ==========================
#   PROGRAMAR ENVÍO
# ==========================
async def schedule_post(context: ContextTypes.DEFAULT_TYPE, user_id):
    await context.job_queue.run_once(
        scheduled_job,
        when=timedelta(minutes=2),
        chat_id=user_id,
        name=f"job_{user_id}"
    )


async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.chat_id

    fake_update = type("obj", (object,), {"effective_user": type("obj2", (object,), {"id": user_id})})
    await send_post(fake_update, context, scheduled=True)


# ==========================
#   MAIN
# ==========================
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(callbacks))

    application.run_polling()


if __name__ == "__main__":
    main()
