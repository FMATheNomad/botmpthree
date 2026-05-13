import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- KONFIGURASI ---
TOKEN = os.getenv("YTMP3_TOKEN", "8621575752:AAEeaPpFsBqoKugNODOynd4jESl9sJOSy0M")
MAX_SIZE_MB = 50                      # Batas ukuran file kiriman Telegram (gratis)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Fungsi download MP3 ---
def download_mp3(url):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        mp3_path = file_path.rsplit('.', 1)[0] + '.mp3'
        return mp3_path, info.get('title', 'Unknown')

# --- Fungsi download MP4 (480p) ---
def download_mp4(url):
    output_dir = "downloads"
    os.makedirs(output_dir, exist_ok=True)
    ydl_opts = {
        'format': 'best[height<=480]',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        if not file_path.endswith('.mp4'):
            mp4_path = file_path.rsplit('.', 1)[0] + '.mp4'
            os.system(f'ffmpeg -i "{file_path}" -c:v libx264 -c:a aac "{mp4_path}" -y')
            os.remove(file_path)
            return mp4_path, info.get('title', 'Unknown')
        return file_path, info.get('title', 'Unknown')

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirim link YouTube, lalu pilih format yang diinginkan:\n"
        "🎵 MP3 (audio saja) atau 🎬 MP4 (video).\n\n"
        "⚠️ Catatan: Telegram hanya mengizinkan file hingga 50 MB. "
        "Kalau videonya terlalu panjang, mungkin ukurannya melebihi batas. "
        "Nanti bot akan memberi tahu jika filenya terlalu besar."
    )

# --- Handler link YouTube, tampilkan tombol MP3 / MP4 ---
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Mohon kirim link YouTube yang valid ya.")
        return

    context.chat_data['last_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("🎵 MP3", callback_data="mp3"),
            InlineKeyboardButton("🎬 MP4", callback_data="mp4"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih format:", reply_markup=reply_markup)

# --- Handler pilihan tombol ---
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
                f"Maaf, ukuran file {size_mb:.1f} MB melebihi batas maksimal {MAX_SIZE_MB} MB "
                "yang diizinkan oleh Telegram.\n"
                "Coba gunakan video yang lebih pendek agar ukurannya lebih kecil."
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
        await query.edit_message_text("Gagal memproses link. Pastikan link masih aktif dan bisa diakses.")

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(button_callback))
    logger.info("Bot MP3/MP4 siap digunakan...")
    app.run_polling()

if __name__ == '__main__':
    main()
