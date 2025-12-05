import os
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    CommandHandler, ContextTypes, filters
)

# ==========================
#   VARIABLES DE ENTORNO
# ==========================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("PERSONAL_ID"))
TARGET_CHANNEL = os.getenv("CHANNEL_ID")

# ==========================
#   ESTADOS POR USUARIO
# ==========================
user_state = {}
media_groups = {}  # <media_group_id>: { "files": [], "caption": "", "complete": False }


# ==========================
#   PERMISO
# ==========================
def allowed(update: Update):
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID


# ==========================
#   EXTRAER LINK Y LIMPIARLO DEL TEXTO
# ==========================
def extract_and_strip_link(text):
    words = text.split()
    link = None
    cleaned_words = []

    for w in words:
        if w.startswith("http://") or w.startswith("https://"):
            link = w
        else:
            cleaned_words.append(w)

    cleaned_text = " ".join(cleaned_words)
    return cleaned_text, link


# ==========================
#   /start
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    text = (
        "👋 *Bienvenido a tu bot de publicación*\n\n"
        "Este bot te permite:\n"
        "• Enviar fotos, vídeos o álbumes\n"
        "• Detectar y formatear enlaces automáticamente\n"
        "• Preguntar tipo de contenido y fuente\n"
        "• Crear vista previa antes de publicar\n"
        "• Elegir entre *Enviar ahora* o *Enviar después*\n\n"
        "Envíame una imagen o un vídeo con texto para comenzar."
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ==========================
#   MANEJAR MEDIA (INCLUYE ÁLBUMES)
# ==========================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allowed(update):
        return

    msg = update.message

    # ==========================
    #     ÁLBUM (media group)
    # ==========================
    if msg.media_group_id:

        group_id = msg.media_group_id

        if group_id not in media_groups:
            caption = msg.caption or ""
            cleaned_caption, detected_link = extract_and_strip_link(caption)

            media_groups[group_id] = {
                "files": [],
                "caption": cleaned_caption,
                "link": detected_link,
                "complete": False,
                "user_id": update.effective_user.id,
            }

        # Añadir archivo
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_groups[group_id]["files"].append(("photo", file_id))

        elif msg.video:
            file_id = msg.video.file_id
            media_groups[group_id]["files"].append(("video", file_id))

        # Detectar si ya llegó todo el álbum
        async def finalize_album(context):
            if group_id in media_groups and not media_groups[group_id]["complete"]:
                media_groups[group_id]["complete"] = True
                await process_full_album(update, context, group_id)

        context.application.create_task(finalize_album(context))
        return

    # ==========================
    #   MENSAJE NORMAL (1 foto / 1 vídeo)
    # ==========================
    if msg.photo:
        files = [("photo", msg.photo[-1].file_id)]
    elif msg.video:
        files = [("video", msg.video.file_id)]
    else:
        await msg.reply_text("Envíame una imagen o un vídeo.")
        return

    cleaned_caption, detected_link = extract_and_strip_link(msg.caption or "")

    await process_new_media(update, context, files, cleaned_caption, detected_link)


# ==========================
#   PROCESAR ÁLBUM COMPLETO
# ==========================
async def process_full_album(update: Update, context, group_id):

    group = media_groups[group_id]

    files = group["files"]
    caption = group["caption"]
    link = group["link"]
    user_id = group["user_id"]

    del media_groups[group_id]

    await process_new_media(update, context, files, caption, link)


# ==========================
#   PROCESAR MEDIA NORMAL O ÁLBUM
# ==========================
async def process_new_media(update, context, files, caption, link):

    user_id = update.effective_user.id

    user_state[user_id] = {
        "files": files,
        "caption": caption,
        "category": None,
        "source": None,
        "link": link,
    }

    # Pregunta categoría
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

    await update.message.reply_text(
        "¿Qué tipo de contenido es?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================
#   CALLBACKS
# ==========================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)
    data = query.data

    if data.startswith("cat_"):
        state["category"] = data.replace("cat_", "")

        if not state["link"]:
            await show_preview_after_category(update, context)
            return

        # Tiene link → pedir fuente
        keyboard = [
            [InlineKeyboardButton("Twitter FE", callback_data="src_TwitterFE")]
        ]

        await query.edit_message_text(
            "He detectado un enlace.\n\nEscribe la *fuente* o elige una:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "src_TwitterFE":
        state["source"] = "Twitter FE"
        await show_preview_after_category(update, context)
        return

    if data == "send_now":
        await send_to_channel(update, context)
        await query.edit_message_text("✔ Publicado en el canal.")
        user_state.pop(user_id, None)
        return

    if data == "send_later":
        await query.edit_message_text("Vista previa generada. Puedes reenviarla cuando quieras.")
        return


# ==========================
#   MANEJAR TEXTO COMO FUENTE
# ==========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)

    if state and state["link"] and state["source"] is None:
        state["source"] = update.message.text
        await show_preview_after_category(update, context)


# ==========================
#   FORMATEAR CAPTION
# ==========================
def format_caption(text, category, source, link):
    parts = text.split("\n")
    formatted = f"*{parts[0]}*"
    if len(parts) > 1:
        formatted += "\n" + "\n".join(parts[1:])

    hashtags = {
        "Noticia": "#Noticia",
        "Estadísticas": "#Estadísticas",
        "Manual": "#ManualFE",
        "Resultados": "#Resultados",
        "Otros": ""
    }

    tag = hashtags.get(category, "")
    if tag:
        formatted += f"\n\n{tag}"

    if link and source:
        formatted += f"\n🔗 [{source}]({link})"

    return formatted


# ==========================
#   MOSTRAR VISTA PREVIA
# ==========================
async def show_preview_after_category(update, context):

    user_id = update.effective_user.id
    state = user_state[user_id]

    formatted = format_caption(
        state["caption"], state["category"], state["source"], state["link"]
    )

    # 🔥 FIX: origen dinámico
    origin = update.message or update.callback_query.message

    # Álbum
    if len(state["files"]) > 1:
        media = []
        for idx, (mtype, fid) in enumerate(state["files"]):
            if mtype == "photo":
                if idx == 0:
                    media.append(InputMediaPhoto(fid, caption=formatted, parse_mode="Markdown"))
                else:
                    media.append(InputMediaPhoto(fid))
            else:
                if idx == 0:
                    media.append(InputMediaVideo(fid, caption=formatted, parse_mode="Markdown"))
                else:
                    media.append(InputMediaVideo(fid))

        await origin.reply_media_group(media)

    # Mensaje simple
    else:
        mtype, fid = state["files"][0]
        if mtype == "photo":
            await origin.reply_photo(fid, caption=formatted, parse_mode="Markdown")
        else:
            await origin.reply_video(fid, caption=formatted, parse_mode="Markdown")

    # Botones enviar ahora / después
    keyboard = [
        [
            InlineKeyboardButton("Enviar ahora", callback_data="send_now"),
            InlineKeyboardButton("Enviar después", callback_data="send_later"),
        ]
    ]

    await origin.reply_text(
        "Aquí tienes la vista previa:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==========================
#   ENVIAR AL CANAL
# ==========================
async def send_to_channel(update, context):

    user_id = update.effective_user.id
    state = user_state[user_id]

    formatted = format_caption(
        state["caption"], state["category"], state["source"], state["link"]
    )

    # Álbum
    if len(state["files"]) > 1:
        media = []
        for idx, (mtype, fid) in enumerate(state["files"]):
            if mtype == "photo":
                if idx == 0:
                    media.append(InputMediaPhoto(fid, caption=formatted, parse_mode="Markdown"))
                else:
                    media.append(InputMediaPhoto(fid))
            else:
                if idx == 0:
                    media.append(InputMediaVideo(fid, caption=formatted, parse_mode="Markdown"))
                else:
                    media.append(InputMediaVideo(fid))

        await context.bot.send_media_group(TARGET_CHANNEL, media)

    # Mensaje simple
    else:
        mtype, fid = state["files"][0]
        if mtype == "photo":
            await context.bot.send_photo(TARGET_CHANNEL, fid, caption=formatted, parse_mode="Markdown")
        else:
            await context.bot.send_video(TARGET_CHANNEL, fid, caption=formatted, parse_mode="Markdown")


# ==========================
#   MAIN
# ==========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.run_polling()


if __name__ == "__main__":
    main()
