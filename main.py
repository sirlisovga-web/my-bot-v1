import logging

logging.basicConfig(
    level=logging.INFO
)
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import yt_dlp
import os
import re
from PIL import Image
from pptx import Presentation

TOKEN = "8621933941:AAEy23zI85JvtRmXnt6alqr8DcTzvBDDvFM"

bot = Bot(token=TOKEN)
dp = Dispatcher()

search_results = {}
user_images = {}
music_search_users = set()  # FIX: bu yerda aniqlanmagan edi, qo'shildi
video_links = {}  # YANGI: foydalanuvchi yuborgan link sifat tanlanguncha shu yerda saqlanadi
video_file_cache = {}  # YANGI: (url, sifat) -> Telegram file_id. Qayta yuklamaslik uchun
music_file_cache = {}  # YANGI: youtube video_id -> Telegram file_id. Qo'shiqni qayta yuklamaslik uchun

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Video Yuklash", callback_data="video")],
        [InlineKeyboardButton(text="🎵 Musiqa Qidirish", callback_data="music")],
        [InlineKeyboardButton(text="🎬 Kino / Multfilm", callback_data="movie")],
        [InlineKeyboardButton(text="📄 Offis Ishlari", callback_data="office")]
    ])

@dp.message(Command("start"))
async def start_command(message: Message):
    # FIX: /start bosilganda foydalanuvchi musiqa qidirish rejimidan
    # chiqariladi — aks holda, oldingi sessiyadan qolib ketgan holat
    # tufayli, /start dan keyin yozilgan har qanday matn (masalan "hi")
    # avtomatik musiqa qidiruvi sifatida qabul qilinardi
    music_search_users.discard(message.from_user.id)
    await message.answer("👋 Assalomu alaykum!\nBotga xush kelibsiz!", reply_markup=main_menu())

# ===================== OFFIS ISHLARI =====================
# DIQQAT: bu bo'lim foydalanuvchi so'rovi bo'yicha o'zgartirilmadi.
@dp.callback_query(F.data == "office")
async def office_menu(callback: CallbackQuery):
    # FIX: boshqa bo'limga o'tilganda musiqa qidirish rejimidan chiqariladi
    music_search_users.discard(callback.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Word → PDF", callback_data="word_to_pdf")],
        [InlineKeyboardButton(text="📊 PPTX → PDF", callback_data="pptx_to_pdf")],
        [InlineKeyboardButton(text="📈 Excel → PDF", callback_data="excel_to_pdf")],
        [InlineKeyboardButton(text="🖼 Rasm(lar) → PDF", callback_data="image_to_pdf")],
        [InlineKeyboardButton(text="🔍 OCR", callback_data="ocr")],
        [InlineKeyboardButton(text="🔙 Asosiy menyuga", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "📄 <b>Offis Ishlari</b>\n\nKerakli funksiyani tanlang:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

# ------------------- Word → PDF -------------------
@dp.callback_query(F.data == "word_to_pdf")
async def word_to_pdf_start(callback: CallbackQuery):
    await callback.message.edit_text("📝 Faqat .docx fayl yuboring.")

@dp.message(F.document & F.document.file_name.endswith('.docx'))
async def convert_word_to_pdf(message: Message):
    await message.answer("📄 Word fayl PDF ga aylantirilmoqda...")
    user_id = message.from_user.id
    docx_path = f"temp_{user_id}.docx"
    pdf_path = f"output_{user_id}.pdf"
    try:
        file = await bot.get_file(message.document.file_id)
        await bot.download_file(file.file_path, docx_path)

        convert(docx_path, pdf_path)

        await message.answer_document(FSInputFile(pdf_path), caption="✅ Word fayl PDF ga aylantirildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:200]}")
    finally:
        if os.path.exists(docx_path):
            os.remove(docx_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

# ------------------- PPTX → PDF -------------------
@dp.callback_query(F.data == "pptx_to_pdf")
async def pptx_to_pdf_start(callback: CallbackQuery):
    await callback.message.edit_text("📊 Faqat .pptx fayl yuboring.")

@dp.message(F.document & F.document.file_name.endswith('.pptx'))
async def convert_pptx_to_pdf(message: Message):
    await message.answer("📊 PPTX fayl PDF ga aylantirilmoqda...")
    await message.answer("⚠️ PPTX → PDF funksiyasi tez orada to'liq ishlaydi.")

# ------------------- Excel → PDF -------------------
@dp.callback_query(F.data == "excel_to_pdf")
async def excel_to_pdf_start(callback: CallbackQuery):
    await callback.message.edit_text("📈 Faqat .xlsx fayl yuboring.")

@dp.message(F.document & F.document.file_name.endswith('.xlsx'))
async def convert_excel_to_pdf(message: Message):
    await message.answer("📈 Excel fayl PDF ga aylantirilmoqda...")
    await message.answer("⚠️ Excel → PDF funksiyasi tez orada to'liq ishlaydi.")

# ------------------- Rasm → PDF -------------------
@dp.callback_query(F.data == "image_to_pdf")
async def image_to_pdf_start(callback: CallbackQuery):
    user_images[callback.from_user.id] = []
    await callback.message.edit_text(
        "🖼 Rasm(lar)ni yuboring.\n\nBarchasini yuborib bo'lgach, /done deb yozing."
    )

@dp.message(F.photo)
async def collect_photos(message: Message):
    user_id = message.from_user.id
    if user_id not in user_images:
        user_images[user_id] = []

    file = await bot.get_file(message.photo[-1].file_id)
    path = f"temp_{user_id}_{len(user_images[user_id])}.jpg"
    await bot.download_file(file.file_path, path)
    user_images[user_id].append(path)

    await message.answer(f"✅ Rasm qabul qilindi ({len(user_images[user_id])} ta)")

@dp.message(Command("done"))
async def convert_to_pdf(message: Message):
    user_id = message.from_user.id
    if user_id not in user_images or not user_images[user_id]:
        await message.answer("Hech qanday rasm yubormadingiz.")
        return

    await message.answer("📄 PDF yaratilmoqda...")
    pdf_path = f"output_{user_id}.pdf"
    try:
        images = [Image.open(img).convert('RGB') for img in user_images[user_id]]
        images[0].save(pdf_path, save_all=True, append_images=images[1:])

        await message.answer_document(FSInputFile(pdf_path), caption="✅ Barcha rasmlar PDF ga aylantirildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:150]}")
    finally:
        for img in user_images.get(user_id, []):
            if os.path.exists(img):
                os.remove(img)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if user_id in user_images:
            del user_images[user_id]

# OCR
@dp.callback_query(F.data == "ocr")
async def ocr_start(callback: CallbackQuery):
    await callback.message.edit_text("🖼 OCR uchun rasm yuboring.")

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    # FIX: boshqa bo'limga (asosiy menyuga) o'tilganda musiqa qidirish
    # rejimidan chiqariladi
    music_search_users.discard(callback.from_user.id)
    await callback.message.edit_text("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu())

# ===================== KINO / MULTFILM =====================
@dp.callback_query(F.data == "movie")
async def movie_menu(callback: CallbackQuery):
    # FIX: boshqa bo'limga o'tilganda musiqa qidirish rejimidan chiqariladi
    music_search_users.discard(callback.from_user.id)
    await callback.message.edit_text(
        "🎬 <b>Kino / Multfilm</b>\n\n"
        "Dasturchimiz hozircha bu bo'limni ishga tushira olmadi, "
        "u buning ustida ishlayapti 👨‍💻",
        parse_mode="HTML"
    )

    await asyncio.sleep(0.8)
    await callback.message.answer(
        "Tez orada qo'shiladi! ⏳"
    )

# ===================== VIDEO =====================
@dp.callback_query(F.data == "video")
async def video_menu(callback: CallbackQuery):
    # FIX: boshqa bo'limga o'tilganda musiqa qidirish rejimidan chiqariladi
    music_search_users.discard(callback.from_user.id)
    await callback.message.edit_text("🎥 Instagram yoki YouTube linkini yuboring.", parse_mode="HTML")

@dp.message(F.text.startswith("http"))
async def receive_video_link(message: Message):
    user_id = message.from_user.id
    url = message.text

    if "instagram.com" in url:
        status = await message.answer("🔄 Instagram videosi yuklanmoqda...")
        await _download_and_send_video(
            message_target=message,
            status=status,
            user_id=user_id,
            url=url,
            format_selector="bestvideo+bestaudio/best",
            quality_label="yuqori sifat"
        )
        return

    video_links[user_id] = url

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔼 Yuqori sifat (1080p)", callback_data="quality_high")],
        [InlineKeyboardButton(text="🔽 Past sifat (480p, tezroq)", callback_data="quality_low")]
    ])
    await message.answer("🎚 Video sifatini tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("quality_"))
async def download_video(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    url = video_links.get(user_id)

    if not url:
        await callback.message.answer("❌ Link topilmadi. Iltimos, linkni qaytadan yuboring.")
        return

    quality = callback.data

    if quality == "quality_high":
        format_selector = "bestvideo+bestaudio/best"
        quality_label = "yuqori sifat"
    else:
        format_selector = "worst[height>=240]/worst"
        quality_label = "past sifat"

    status = await callback.message.answer("🔎 Video tekshirilmoqda...")
    await _download_and_send_video(
        message_target=callback.message,
        status=status,
        user_id=user_id,
        url=url,
        format_selector=format_selector,
        quality_label=quality_label
    )


async def _download_and_send_video(message_target, status, user_id, url, format_selector, quality_label):
    cache_key = (url, format_selector)
    cached_file_id = video_file_cache.get(cache_key)
    if cached_file_id:
        try:
            caption = "📥 Video @ishbilarmonnodirjon_bot tomonidan yuklab olindi"
            await message_target.answer_video(cached_file_id, caption=caption)
            await status.delete()
            return True
        except Exception:
            video_file_cache.pop(cache_key, None)

    filename = None
    try:
        ydl_opts = {
            'outtmpl': f'video_{user_id}.%(ext)s',
            'format': format_selector,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'cookiefile': '/etc/secrets/cookies.txt',
            'no_cookies_update': True,
            'cookies_update': False,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            estimated_bytes = info.get('filesize') or info.get('filesize_approx')

            if not estimated_bytes and info.get('requested_formats'):
                sizes = [
                    f.get('filesize') or f.get('filesize_approx') or 0
                    for f in info['requested_formats']
                ]
                if all(sizes):
                    estimated_bytes = sum(sizes)

            if estimated_bytes:
                estimated_mb = estimated_bytes / (1024 * 1024)
                if estimated_mb > 50:
                    await status.edit_text(
                        f"⚠️ Video juda katta (~{estimated_mb:.1f} MB).\n\n"
                        f"Telegram bot orqali faqat 50MB gacha fayl yuborish mumkin. "
                        f"Iltimos, \"📉 Past sifat\" tugmasini tanlang — fayl hajmi kichikroq bo'ladi."
                    )
                    return False

            await status.edit_text(f"🔄 {quality_label}da yuklanmoqda...")
            ydl.download([url])
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4_path = base + ".mp4"
            if os.path.exists(mp4_path):
                filename = mp4_path

        if filename and os.path.exists(filename):
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

            if file_size_mb > 50:
                await status.edit_text(
                    f"⚠️ Video juda katta ({file_size_mb:.1f} MB).\n\n"
                    f"Telegram bot orqali faqat 50MB gacha fayl yuborish mumkin. "
                    f"Iltimos, \"📉 Past sifat\" tugmasini tanlang — fayl hajmi kichikroq bo'ladi."
                )
                return False
            else:
                caption = "📥 Video @ishbilarmonnodirjon_bot tomonidan yuklab olindi"
                sent_message = await message_target.answer_video(FSInputFile(filename), caption=caption)
                video_file_cache[cache_key] = sent_message.video.file_id
                await status.delete()
                return True
        else:
            await status.edit_text("❌ Video topilmadi yoki yuklab bo'lmadi.")
            return False
    except Exception as e:
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")
        return False
    finally:
        if filename and os.path.exists(filename):
            for attempt in range(5):
                try:
                    os.remove(filename)
                    break
                except PermissionError:
                    await asyncio.sleep(0.5)

# ===================== MUSIQA =====================
@dp.callback_query(F.data == "music")
async def music_menu(callback: CallbackQuery):
    await callback.answer()

    music_search_users.add(callback.from_user.id)

    await callback.message.edit_text(
        "🎵 Qo'shiq nomini yozing.\n\nMasalan:\nAdele Hello"
    )

async def search_music(message: Message):
    user_id = message.from_user.id

    if user_id not in music_search_users:
        return

    # FIX: endi qidiruvdan keyin foydalanuvchi rejimdan chiqarilmaydi —
    # "Musiqa Qidirish" tugmasi bir marta bosilgach, foydalanuvchi shu
    # rejimda qoladi va istalgancha marta, tugmani qayta bosmasdan,
    # yangi qo'shiq nomi yozib qidira oladi. Rejimdan faqat boshqa
    # bo'limga (video, office va h.k.) o'tilganda chiqariladi.

    status = await message.answer("🔎 Qidirilmoqda...")

    try:
        with yt_dlp.YoutubeDL(
            {
                "quiet": True,
                "extract_flat": True,
                "default_search": "ytsearch5"
            }
        ) as ydl:
            result = ydl.extract_info(f"ytsearch5:{message.text}", download=False)

        entries = result.get("entries", [])

        if not entries:
            await status.edit_text("❌ Hech narsa topilmadi.")
            return

        search_results[user_id] = entries

        keyboard = []

        for i, entry in enumerate(entries):
            title = entry.get("title", "Unknown")

            if len(title) > 50:
                title = title[:50] + "..."

            keyboard.append([
                InlineKeyboardButton(
                    text=f"{i + 1}. {title}",
                    callback_data=f"music_select_{i}"
                )
            ])

        await status.edit_text(
            "🎵 Natijalar:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    except Exception as e:
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")

@dp.message(F.text & ~F.text.startswith("http"))
async def handle_text(message: Message):
    await search_music(message)

@dp.callback_query(F.data.startswith("music_select_"))
async def select_music(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id

    if user_id not in search_results:
        await callback.message.answer("❌ Natijalar eskirgan. Qayta qidiring.")
        return

    index = int(callback.data.split("_")[-1])

    try:
        song = search_results[user_id][index]
    except (IndexError, KeyError):
        await callback.message.answer("❌ Qo'shiq topilmadi. Qayta qidiring.")
        return

    title = song.get("title", "Unknown")
    channel = song.get("channel", "Unknown")
    video_id = song.get("id")
    url = f"https://www.youtube.com/watch?v={video_id}"

    status = await callback.message.answer(f"⬇️ \"{title}\" yuklanmoqda...")

    cached_file_id = music_file_cache.get(video_id)
    if cached_file_id:
        try:
            caption = "📥 Qo'shiq @ishbilarmonnodirjon_bot tomonidan yuklab olindi"
            await callback.message.answer_audio(cached_file_id, caption=caption)
            await status.delete()
            return
        except Exception:
            music_file_cache.pop(video_id, None)

    audio_path = f"audio_{callback.from_user.id}.mp3"
    try:
        ydl_opts = {
            # FIX: aniqroq format ro'yxati — ba'zi formatlar (ayniqsa "web"
            # klientidan kelganlari) "416 Requested Range Not Satisfiable"
            # xatosini berishi mumkin. m4a/webm aniq ro'yxatlanganda bu kamroq
            # uchraydi.
            'cookiefile': '/etc/secrets/cookies.txt',
            'no_cookies_update': True,
            'cookies_update': False,
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': f'audio_{callback.from_user.id}.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # FIX: YouTube'ning "android" klienti JavaScript runtime talab
            # qilmaydi va "416" xatosiga kamroq uchraydi (web klientidan farqli)
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
        }

        max_attempts = 3
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
                last_error = None
                break
            except Exception as e:
                last_error = e
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if attempt < max_attempts:
                    await status.edit_text(f"⚠️ Urinish {attempt} muvaffaqiyatsiz, qayta urinilmoqda...")
                    await asyncio.sleep(2)

        if last_error is not None:
            raise last_error

        if not os.path.exists(audio_path):
            await status.edit_text("❌ Audio fayl yaratilmadi. Qayta urinib ko'ring.")
            return

        safe_title = title if title and title != "Unknown" else "Music"
        safe_title = re.sub(r'[\\/*?:"<>|]', "", safe_title).strip()
        if not safe_title:
            safe_title = "Music"
        display_filename = f"{safe_title[:150]}.mp3"

        caption = "📥 Qo'shiq @ishbilarmonnodirjon_bot tomonidan yuklab olindi"
        sent_message = await callback.message.answer_audio(
            FSInputFile(audio_path, filename=display_filename),
            caption=caption
        )
        if video_id:
            music_file_cache[video_id] = sent_message.audio.file_id
        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Yuklashda xatolik: {str(e)[:200]}")
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
