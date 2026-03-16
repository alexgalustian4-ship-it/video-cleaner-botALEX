import os
import sys
import subprocess
import tempfile
import logging
import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "COLLE_TON_TOKEN_ICI")

def ensure_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("FFmpeg OK")
        return True
    except Exception:
        logger.info("FFmpeg non trouvé, installation...")
        try:
            subprocess.run(["apt-get", "update", "-y"], capture_output=True)
            subprocess.run(["apt-get", "install", "-y", "ffmpeg"], capture_output=True)
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("FFmpeg installé avec succès")
            return True
        except Exception as e:
            logger.error(f"Impossible d'installer FFmpeg: {e}")
            return False

def random_date():
    base = datetime(2024, 6, 1)
    d = base + timedelta(days=random.randint(0, 180), hours=random.randint(8, 20), minutes=random.randint(0, 59))
    return d.strftime("%Y-%m-%dT%H:%M:%S")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Envoie ta vidéo en tant que Fichier (📎 → Fichier) et je nettoie les métadonnées automatiquement."
    )

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.mime_type or not doc.mime_type.startswith("video/"):
        await update.message.reply_text("⚠️ Envoie une vidéo en tant que Fichier (📎 → Fichier).")
        return
    if doc.file_size > 50 * 1024 * 1024:
        await update.message.reply_text("⚠️ Fichier trop lourd. Maximum 50MB.")
        return

    msg = await update.message.reply_text("⏳ Traitement en cours...")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ext = ("." + doc.file_name.rsplit(".", 1)[-1]) if doc.file_name and "." in doc.file_name else ".mp4"
            inp = os.path.join(tmp, "input" + ext)
            out = os.path.join(tmp, "clean" + ext)

            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(inp)

            cmd = [
                "ffmpeg", "-i", inp,
                "-map_metadata", "-1",
                "-metadata", "make=Apple",
                "-metadata", "model=iPhone 15 Pro",
                "-metadata", "encoder=CapCut 5.2",
                "-metadata", "software=CapCut 5.2",
                "-metadata", f"creation_time={random_date()}",
                "-c", "copy", "-y", out
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                await msg.edit_text("❌ Erreur FFmpeg.")
                return

            with open(out, "rb") as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename="clean_" + (doc.file_name or "video" + ext),
                    caption="✅ Vidéo nettoyée — métadonnées remplacées."
                )
            await msg.delete()

    except subprocess.TimeoutExpired:
        await msg.edit_text("❌ Timeout.")
    except Exception as e:
        logger.error(e)
        await msg.edit_text(f"❌ Erreur : {e}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ Envoie la vidéo en tant que *Fichier* (📎 → Fichier) pour garder la qualité originale.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    ensure_ffmpeg()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    logger.info("Bot démarré")
    app.run_polling()
