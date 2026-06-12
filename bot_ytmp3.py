import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pytubefix import YouTube
from pytubefix.cli import on_progress

TOKEN = os.getenv("YTMP3_TOKEN", "8621575752:AAGNPpfJPt47e-u3E4ciVvTiqearqvQ4HzU")
MAX_SIZE_MB = 50

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def download_mp3(url):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    yt = YouTube(url, on_progress_callback=on_progress)
    stream = yt.streams.get_audio_only()
    if not stream:
        raise Exception("No audio stream available")
    out_file = stream.download(output_path=output_dir)
    mp3_path = out_file.rsplit('.', 1)[0] + '.mp3'
    os.rename(out_file, mp3_path)
    return mp3_path, yt.title


def download_mp4(url):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    yt = YouTube(url, on_progress_callback=on_progress)
    stream = yt.streams.get_highest_resolution()
    if not stream:
        stream = yt.streams.filter(progressive=True).first()
    if not stream:
        raise Exception("No video stream available")
    out_file = stream.download(output_path=output_dir)
    if not out_file.endswith('.mp4'):
        mp4_path = out_file.rsplit('.', 1)[0] + '.mp4'
        os.rename(out_file, mp4_path)
        return mp4_path, yt.title
    return out_file, yt.title


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirim link YouTube, lalu pilih format:\n"
        "🎵 MP3 (audio saja) atau 🎬 MP4 (video).\n\n"
        "⚠️ Maks 50 MB."
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Mohon kirim link YouTube yang valid.")
        return
    context.chat_data['last_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
            InlineKeyboardButton("🎬 MP4", callback_data="mp4"),
        ]
    ]
    await update.message.reply_text("Pilih format:", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    url = context.chat_data.get('last_url')
    if not url:
        await query.edit_message_text("Link tidak tersedia, silakan kirim ulang.")
        return
    await query.edit_message_text("Sedang diunduh, mohon tunggu... ⏳")
    try:
        if choice == 'mp3':
            file_path, title = download_mp3(url)
        else:
            file_path, title = download_mp4(url)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > MAX_SIZE_MB:
            await query.edit_message_text(
                f"Maaf, ukuran file {size_mb:.1f} MB melebihi batas 50 MB."
            )
            os.remove(file_path)
            return
        with open(file_path, 'rb') as f:
            if choice == 'mp3':
                await query.message.reply_audio(audio=f, title=title, performer="YouTube")
            else:
                await query.message.reply_video(video=f, caption=title)
        await query.edit_message_text("✅ Berhasil! File sudah dikirim.")
        os.remove(file_path)
    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text("Gagal memproses link. Pastikan link masih aktif.")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Bot siap...")
    app.run_polling()


if __name__ == '__main__':
    main()
