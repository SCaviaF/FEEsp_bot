import os
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CallbackQueryHandler,
    ContextTypes, CommandHandler, filters
)

# ==========================
#   VARIABLES DE ENTORNO
# ==========================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USER_ID = int(os.getenv("PERSONAL_ID"))
TARGET_CHANNEL = os.getenv("CHANNEL_ID")  # Ejemplo: "@FormulaEEsp"

# ==========================
#   SESIÓN DE USUARIO
# ==========================
user_state = {}  # Memoria temporal por usuario (imagen/video + texto + pasos)


# ==========================
#   CHECK DE PERMISOS
# ==========================
def allowed(update: Update):
    return update.effective_user and update.effective_user.id == ALLOWED_USER_ID

# ==========================
#   MENSAJE DE BIENVENIDA
# ==========================

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    message = (
        "👋 ¡Bienvenido al Bot de Gestión de Contenidos!\n\n"
        "Este bot permite:\n"
        "1️⃣ Enviar imágenes o vídeos con texto a tu canal.\n"
        "2️⃣ Clasificar el contenido mediante botones: Noticia, Estadísticas, Manual, Resultados u Otros.\n"
        "3️⃣ Indicar la fuente del contenido.\n"
        "4️⃣ Elegir si enviar el contenido inmediatamente o programarlo para una fecha y hora específica.\n"
        "5️⃣ Cuando se programa un mensaje, recibirás una confirmación con el contenido y la fecha/hora.\n"
        "6️⃣ Cancelar cualquier mensaje programado antes de que se envíe con el comando /cancelar.\n"
        "7️⃣ Formato automático: primer párrafo en negrita, hashtags según categoría, enlace de la fuente y botón SUSCRÍBETE.\n\n"
        "📌 Para comenzar, envía una imagen o vídeo con el texto que quieras publicar."
    )

    await update.message.reply_text(message)

application.add_handler(CommandHandler("start", start_bot))

# ==========================
#   RECEPCIÓN DE MEDIA
# ==========================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    message = update.message

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = "photo"
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

    user_state[user_id] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": message.caption,
        "category": None,
        "source": None,
        "schedule_datetime": None,
        "job": None
    }

    keyboard = [
        [InlineKeyboardButton("Noticia", callback_data="cat_Noticia"),
         InlineKeyboardButton("Estadísticas", callback_data="cat_Estadísticas")],
        [InlineKeyboardButton("Manual", callback_data="cat_Manual"),
         InlineKeyboardButton("Resultados", callback_data="cat_Resultados")],
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
            await query.edit_message_text(
                "Introduce la fecha y hora de envío en formato DD/MM/YYYY HH:MM\nEjemplo: 05/12/2025 15:30"
            )
        return


# ==========================
#   MANEJAR TEXTO COMO FUENTE O FECHA
# ==========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)
    text = update.message.text

    if state:
        # Paso fuente
        if state["category"] and state["source"] is None:
            state["source"] = text
            keyboard = [
                [InlineKeyboardButton("Enviar ahora", callback_data="send_now"),
                 InlineKeyboardButton("Programar", callback_data="send_later")]
            ]
            await update.message.reply_text(
                f"Fuente guardada: {state['source']}\n\n¿Enviar ahora o programar?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # Paso fecha/hora
        elif state["category"] and state["source"] and state["schedule_datetime"] is None:
            try:
                send_datetime = datetime.strptime(text, "%d/%m/%Y %H:%M")
                if send_datetime < datetime.now():
                    await update.message.reply_text("La fecha/hora debe ser en el futuro.")
                    return

                state["schedule_datetime"] = send_datetime
                job = context.job_queue.run_once(
                    scheduled_job,
                    when=(send_datetime - datetime.now()).total_seconds(),
                    chat_id=user_id,
                    name=f"job_{user_id}"
                )
                state["job"] = job

                await update.message.reply_text(
                    f"✅ Mensaje programado para {send_datetime.strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"Contenido:\n{format_caption(state['caption'], state['category'], state['source'])}\n\n"
                    "Si quieres cancelar el envío antes de que ocurra, usa /cancelar."
                )

            except ValueError:
                await update.message.reply_text(
                    "Formato incorrecto. Usa DD/MM/YYYY HH:MM\nEjemplo: 05/12/2025 15:30"
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

    hashtags = {"Noticia": "#Noticia", "Estadísticas": "#Estadísticas",
                "Manual": "#ManualFE", "Resultados": "#Resultados", "Otros": ""}

    tag = hashtags.get(category, "")
    if tag:
        final_text += f"\n\n{tag}"

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
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("SUSCRÍBETE", url="https://t.me/FormulaEEsp")]])

    if state["media_type"] == "photo":
        await context.bot.send_photo(chat_id=TARGET_CHANNEL, photo=state["file_id"],
                                     caption=formatted, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await context.bot.send_video(chat_id=TARGET_CHANNEL, video=state["file_id"],
                                     caption=formatted, parse_mode="Markdown", reply_markup=keyboard)

    if not scheduled:
        await update.message.reply_text("✔ Publicado en el canal.")

    user_state.pop(user_id, None)


# ==========================
#   JOB PROGRAMADO
# ==========================
async def scheduled_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.chat_id
    fake_update = type("obj", (object,), {"effective_user": type("obj2", (object,), {"id": user_id})})
    await send_post(fake_update, context, scheduled=True)
    state = user_state.get(user_id)
    if state:
        state["job"] = None
        state["schedule_datetime"] = None


# ==========================
#   CANCELAR MENSAJE PROGRAMADO
# ==========================
async def cancel_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    user_id = update.effective_user.id
    state = user_state.get(user_id)
    if state and state.get("job"):
        state["job"].schedule_removal()
        state["job"] = None
        state["schedule_datetime"] = None
        await update.message.reply_text("❌ Mensaje programado cancelado.")
    else:
        await update.message.reply_text("No tienes mensajes programados.")


# ==========================
#   MAIN
# ==========================
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(callbacks))
    application.add_handler(CommandHandler("cancelar", cancel_scheduled))

    application.run_polling()


if __name__ == "__main__":
    main()

