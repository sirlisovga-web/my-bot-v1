import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import yt_dlp
import os
from PIL import Image
from docx2pdf import convert
from pptx import Presentation

TOKEN = "8621933941:AAEy23zI85JvtRmXnt6alqr8DcTzvBDDvFM"

bot = Bot(token="8621933941:AAEy23zI85JvtRmXnt6alqr8DcTzvBDDvFM")
dp = Dispatcher()

search_results = {}
user_images = {}

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Video Yuklash", callback_data="video")],
        [InlineKeyboardButton(text="🎵 Musiqa Qidirish", callback_data="music")],
        [InlineKeyboardButton(text="🎬 Kino / Multfilm", callback_data="movie")],
        [InlineKeyboardButton(text="📄 Offis Ishlari", callback_data="office")]
    ])

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer("👋 Assalomu alaykum!\nBotga xush kelibsiz!", reply_markup=main_menu())

# ===================== OFFIS ISHLARI =====================
@dp.callback_query(F.data == "office")
async def office_menu(callback: CallbackQuery):
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
    try:
        file = await bot.get_file(message.document.file_id)
        docx_path = "temp.docx"
        pdf_path = "output.pdf"
        await bot.download_file(file.file_path, docx_path)
        
        convert(docx_path, pdf_path)
        
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Word fayl PDF ga aylantirildi!")
        
        os.remove(docx_path)
        os.remove(pdf_path)
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:200]}")

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
        "🖼 Rasm(lar)ni yuboring.\n\nBarchasini yuborib bo‘lgach, `/done` deb yozing."
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

@dp.message(F.text == "/done")
async def convert_to_pdf(message: Message):
    user_id = message.from_user.id
    if user_id not in user_images or not user_images[user_id]:
        await message.answer("Hech qanday rasm yubormadingiz.")
        return

    await message.answer("📄 PDF yaratilmoqda...")
    try:
        images = [Image.open(img).convert('RGB') for img in user_images[user_id]]
        pdf_path = f"output_{user_id}.pdf"
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        
        await message.answer_document(FSInputFile(pdf_path), caption="✅ Barcha rasmlar PDF ga aylantirildi!")
        
        for img in user_images[user_id]:
            if os.path.exists(img):
                os.remove(img)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        del user_images[user_id]
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)[:150]}")

# OCR
@dp.callback_query(F.data == "ocr")
async def ocr_start(callback: CallbackQuery):
    await callback.message.edit_text("🖼 OCR uchun rasm yuboring.")

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu())

# ===================== KINO / MULTFILM =====================
@dp.callback_query(F.data == "movie")
async def movie_menu(callback: CallbackQuery):
    # 1-habar
    await callback.message.edit_text(
        "🎬 <b>Kino / Multfilm</b>\n\n"
        "Dasturchimiz hozircha bu bo'limni ishga tushira olmadi, "
        "u buning ustida ishlayapti 👨‍💻",
        parse_mode="HTML"
    )
    
    # 2-habar (alohida)
    await asyncio.sleep(0.8)
    await callback.message.answer(
        "Tez orada qo'shiladi! ⏳"
    )

# ===================== VIDEO VA MUSIQA =====================
@dp.callback_query(F.data == "video")
async def video_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎥 Instagram yoki YouTube linkini yuboring.", parse_mode="HTML")

@dp.message(F.text.startswith("http"))
async def download_video(message: Message):
    status = await message.answer("🔄 Yuklanmoqda... Iltimos biroz kuting.")
    try:
        ydl_opts = {
            'outtmpl': '%(title)s.%(ext)s',
            'format': 'best[height<=720]/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_retries': 3,
            'socket_timeout': 30,
            # Instagram uchun qo'shimcha parametrlar
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(message.text, download=True)
            filename = ydl.prepare_filename(info)
        
        if os.path.exists(filename):
            await message.answer_video(FSInputFile(filename), caption=info.get('title', 'Video'))
            os.remove(filename)
            await status.delete()
        else:
            await status.edit_text("❌ Fayl topilmadi.")
            
    except Exception as e:
        error_str = str(e)
        if "empty media response" in error_str or "Instagram" in error_str:
            await status.edit_text("❌ Instagramdan yuklashda muammo. Post ochiq emas yoki Instagram himoyasi kuchaygan.\n\nBoshqa Instagram linkini sinab ko'ring.")
        else:
            await status.edit_text(f"❌ Xatolik: {error_str[:250]}")

@dp.callback_query(F.data == "music")
async def music_menu(callback: CallbackQuery):
    await callback.message.edit_text("🎵 Musiqa Qidirish\n\nQo'shiq nomini yozing.", parse_mode="HTML")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())