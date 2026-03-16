import os
import subprocess
import tempfile
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "COLLE_TON_TOKEN_ICI")

PRESETS = {
    "iphone": {"device": "iPhone 15 Pro", "encoder": "Apple iPhone", "artist": ""},
    "samsung": {"device": "Samsung Galaxy S24", "encoder": "Samsung Camera", "artist": ""},
    "capcut": {"device": "iPhone 14", "encoder": "CapCut 5.2", "artist": ""},
    "davinci": {"device": "Sony A7 IV", "encoder": "DaVinci Resolve 18", "artist": ""},
}

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 iPhone 15 Pro", callback_data="preset_iphone"),
         InlineKeyboardButton("📱 Samsung S24", callback_data="preset_samsung")],
        [InlineKeyboardButton("🎬 CapCut", callback_data="preset_capcut"),
         InlineKeyboardButton("🎥 DaVinci", callback_data="preset_davinci")],
        [InlineKeyboardButton("✏️ Personnalisé", callback_data="preset_custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 *Alex Management — Video Cleaner*\n\n"
        "Choisis un preset de métadonnées, ensuite envoie ta vidéo :",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("preset_"):
        preset_key = query.data.replace("preset_", "")
        if preset_key == "custom":
            user_data[user_id] = {"mode": "custom", "step": "device"}
            await query.edit_message_text("✏️ *Mode personnalisé*\n\nEnvoie le nom de l'appareil (ex: iPhone 14 Pro) :", parse_mode="Markdown")
        else:
            preset = PRESETS[preset_key]
            user_data[user_id] = {"mode": "preset", **preset}
            await query.edit_message_text(
                f"✅ Preset *{preset_key.capitalize()}* sélectionné\n\n"
                f"• Appareil : `{preset['device']}`\n"
                f"• Logiciel : `{preset['encoder']}`\n\n"
                f"Maintenant envoie ta vidéo en tant que *fichier* (📎 Attach → File) :",
                parse_mode="Markdown"
            )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data.get(user_id, {})

    if data.get("mode") == "custom":
        step = data.get("step")
        if step == "device":
            user_data[user_id]["device"] = update.message.text
            user_data[user_id]["step"] = "encoder"
            await update.message.reply_text("🎬 Nom du logiciel (ex: CapCut 5.2, DaVinci Resolve) :")
        elif step == "encoder":
            user_data[user_id]["encoder"] = update.message.text
            user_data[user_id]["step"] = "artist"
            await update.message.reply_text("👤 Nom de l'auteur/artiste (ou envoie `-` pour ignorer) :")
        elif step == "artist":
            artist = update.message.text if update.message.text != "-" else ""
            user_data[user_id]["artist"] = artist
            user_data[user_id]["step"] = None
            await update.message.reply_text(
                f"✅ Config personnalisée sauvegardée\n\n"
                f"• Appareil : `{user_data[user_id]['device']}`\n"
                f"• Logiciel : `{user_data[user_id]['encoder']}`\n"
                f"• Auteur : `{artist or 'aucun'}`\n\n"
                f"Maintenant envoie ta vidéo en tant que *fichier* (📎 Attach → File) :",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("Utilise /start pour commencer.")

async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = user_data.get(user_id)

    if not data:
        await update.message.reply_text("Utilise /start d'abord pour choisir un preset.")
        return

    doc = update.message.document
    if not doc:
        await update.message.reply_text(
            "⚠️ Envoie la vidéo en tant que *fichier* (📎 Attach → File), pas comme vidéo — pour garder la qualité originale.",
            parse_mode="Markdown"
        )
        return

    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        await update.message.reply_text("⚠️ Ce fichier n'est pas une vidéo.")
        return

    if doc.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("⚠️ Fichier trop lourd. Maximum 50MB.")
        return

    msg = await update.message.reply_text("⏳ Traitement en cours...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input" + _get_ext(doc.file_name))
            output_path = os.path.join(tmpdir, "clean_" + (doc.file_name or "video.mp4"))

            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(input_path)

            device = data.get("device", "iPhone 15 Pro")
            encoder = data.get("encoder", "Apple iPhone")
            artist = data.get("artist", "")

            cmd = [
                "ffmpeg", "-i", input_path,
                "-map_metadata", "-1",
                "-metadata", f"make={device}",
                "-metadata", f"model={device}",
                "-metadata", f"encoder={encoder}",
                "-metadata", f"software={encoder}",
                "-metadata", f"creation_time={_random_date()}",
            ]

            if artist:
                cmd += ["-metadata", f"artist={artist}", "-metadata", f"title={artist}"]

            cmd += ["-c", "copy", "-y", output_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                await msg.edit_text("❌ Erreur FFmpeg. Vérifie que le fichier est une vidéo valide.")
                return

            await msg.edit_text("✅ Métadonnées nettoyées — envoi du fichier...")

            with open(output_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=output_path.split("/")[-1],
                    caption=f"✅ *Vidéo nettoyée*\n• Appareil : `{device}`\n• Logiciel : `{encoder}`",
                    parse_mode="Markdown"
                )

            await msg.delete()

    except subprocess.TimeoutExpired:
        await msg.edit_text("❌ Timeout — fichier trop long à traiter.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await msg.edit_text(f"❌ Erreur inattendue : {str(e)}")

def _get_ext(filename):
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1]
    return ".mp4"

def _random_date():
    import random
    from datetime import datetime, timedelta
    base = datetime(2024, 1, 1)
    rand_days = random.randint(0, 365)
    rand_hours = random.randint(8, 20)
    rand_mins = random.randint(0, 59)
    d = base + timedelta(days=rand_days, hours=rand_hours, minutes=rand_mins)
    return d.strftime("%Y-%m-%dT%H:%M:%S")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("Bot démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()
