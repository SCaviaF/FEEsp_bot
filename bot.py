import os
import re
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
media_groups = {}  # <media_group_id>: { "files": [], "caption": "", "link": "", "user_id": "" }


# ==========================
#   PERMISO
# ==========================
def allowed(update: Update):
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID


# ==========================
#   EXTRAER LINK Y LIMPIARLO (PRESERVANDO SALTOS DE LÍNEA)
# ==========================
URL_RE = re.compile(r'(https?://\S+)', re.IGNORECASE)


def extract_and_strip_link(text: str):
    """
    Devuelve (cleaned_text, link)
    - Si hay un link (la primera coincidencia), lo extrae y lo elimina del texto
    - Preserva saltos de línea en el texto devuelto
    """
    if not text:
        return text, None

    m = URL_RE.search(text)
    if not m:
        return text, None

    link = m.group(1)

    # Eliminar solo la ocurrencia exacta del link
    cleaned = text.replace(link, "")

    # Quitar espacios múltiples pero mantener saltos de línea:
    # - colapsar espacios/tabs dentro de líneas
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    # - limpiar finales de línea
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    # - eliminar líneas vacías múltiples al inicio/final
    cleaned = cleaned.strip()

    return cleaned, link


# ==========================
#   /start
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    text = (
        "👋 *Bienvenido a tu bot de publicación*\n\n"
        "Funciones breves:\n"
        "• Enviar fotos, vídeos o álbumes\n"
        "• Detecta enlaces y los mueve al final formateados\n"
        "• Pregunta tipo de contenido y (si hay link) la fuente\n"
        "• Vista previa antes de publicar\n"
        "• Elegir: *Enviar ahora* o *Enviar después*\n\n"
        "Envíame una imagen, vídeo o álbum con texto para comenzar."
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

        # Añadir archivo al grupo
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_groups[group_id]["files"].append(("photo", file_id))

        elif msg.video:
            file_id = msg.video.file_id
            media_groups[group_id]["files"].append(("video", file_id))

        # Telegram no indica fin del álbum; finalizamos en la siguiente iteración ligera
        async def finalize_album(context):
            if group_id in media_groups and not media_groups[group_id]["complete"]:
                media_groups[group_id]["complete"] = True
                await process_full_album(update, context, group_id)

        # schedule as task (quick)
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

    # borrar estado de grupo
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

    if not state:
        await query.edit_message_text("No hay ninguna publicación en proceso.")
        return

    if data.startswith("cat_"):
        state["category"] = data.replace("cat_", "")

        if not state["link"]:
            await show_preview_after_category(update, context)
            return

        # Tiene link → pedir fuente (opción rápida Twitter FE)
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
        # eliminar botones de la vista previa y dejar la vista previa como está
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

    # Si estamos pidiendo fuente (hay link y aún no hay source)
    if state and state.get("link") and state.get("source") is None:
        state["source"] = update.message.text
        await show_preview_after_category(update, context)


# ==========================
#   FORMATEAR CAPTION (PRIMER PÁRRAFO EN NEGRITA, RESTO CON SALTOS)
# ==========================
def format_caption(text, category, source, link):
    """
    - Mantiene saltos de línea.
    - Pone en negrita el primer párrafo (definido como el bloque antes de la primera línea vacía).
    - Añade hashtag y línea de enlace formateada si procede.
    """
    if not text:
        first = ""
        rest = ""
    else:
        # Separar por párrafos (bloques separados por línea vacía)
        parts = text.split("\n\n", 1)
        first = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""

    formatted = ""
    if first:
        formatted += f"*{first}*"
    if rest:
        # conservar el doble salto que separa párrafos
        formatted += "\n\n" + rest

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
        # Añadir la línea del enlace al final (formateada) — sólo aparece aquí
        formatted += f"\n\n🔗 [{source}]({link})"

    return formatted


# ==========================
#   MOSTRAR VISTA PREVIA (ORIGEN DINÁMICO) + BOTÓN SUSCRÍBETE
# ==========================
async def show_preview_after_category(update, context):

    user_id = update.effective_user.id
    state = user_state[user_id]

    formatted = format_caption(
        state["caption"], state["category"], state["source"], state["link"]
    )

    # FIX: origen puede ser message o callback_query.message
    origin = update.message or (update.callback_query and update.callback_query.message)

    # Botón SUSCRÍBETE (como mensaje separado cuando sea un álbum)
    subscribe_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]
    ])

    # Preparar media (álbum o único)
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

        # Enviar álbum (no admite reply_markup). Luego enviar botón SUSCRÍBETE en mensaje separado.
        await origin.reply_media_group(media)
        await origin.reply_text("🔔 Suscríbete:", reply_markup=subscribe_kb)

    else:
        mtype, fid = state["files"][0]
        if mtype == "photo":
            # send_photo admite reply_markup
            await origin.reply_photo(fid, caption=formatted, parse_mode="Markdown", reply_markup=subscribe_kb)
        else:
            await origin.reply_video(fid, caption=formatted, parse_mode="Markdown", reply_markup=subscribe_kb)

    # Botones enviar ahora / después (separados)
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
#   ENVIAR AL CANAL (INCLUYE SUSCRÍBETE)
# ==========================
async def send_to_channel(update, context):

    user_id = update.effective_user.id
    state = user_state[user_id]

    formatted = format_caption(
        state["caption"], state["category"], state["source"], state["link"]
    )

    subscribe_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]
    ])

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

        # send_media_group no acepta reply_markup → enviamos grupo y luego mensaje con botón
        await context.bot.send_media_group(TARGET_CHANNEL, media)
        await context.bot.send_message(chat_id=TARGET_CHANNEL, text="🔔 Suscríbete:", reply_markup=subscribe_kb)

    # Mensaje simple
    else:
        mtype, fid = state["files"][0]
        if mtype == "photo":
            await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=fid, caption=formatted, parse_mode="Markdown", reply_markup=subscribe_kb)
        else:
            await context.bot.send_video(chat_id=TARGET_CHANNEL, video=fid, caption=formatted, parse_mode="Markdown", reply_markup=subscribe_kb)


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

