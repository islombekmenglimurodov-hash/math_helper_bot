# main.py
import re
import os
import asyncio
import configparser

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import pytesseract
from PIL import Image
import sympy as sp

# -----------------------
# Config
# -----------------------
config = configparser.ConfigParser()
config.read("config.ini")
API_TOKEN = config.get("DEFAULT", "TOKEN", fallback=None)

if not API_TOKEN or "YOUR" in (API_TOKEN or ""):
    raise SystemExit("ERROR: config.ini ichiga token qo'ying.")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# -----------------------
# OCR helper
# -----------------------
def ocr_from_image(path: str) -> str:
    try:
        text = pytesseract.image_to_string(Image.open(path), lang="eng+rus+uzb")
        return text.strip()
    except:
        return ""

# ---------------------------------------------------------------
# MATH LOGIC (simple)
# ---------------------------------------------------------------

def try_parse_and_solve_equation(text: str):
    t = text.replace("−", "-").replace(",", ".")
    if "=" not in t:
        return False, None

    try:
        left, right = t.split("=", 1)
        L = sp.sympify(left)
        R = sp.sympify(right)
        eq = sp.Eq(L, R)
    except Exception:
        return False, None

    try:
        vars_in_eq = sorted(list(eq.free_symbols), key=lambda s: str(s))
        if len(vars_in_eq) == 1:
            var = vars_in_eq[0]
            sol = sp.solve(eq, var)
            if not sol:
                return True, "❌ Yechim yo'q yoki cheksiz yechim."
            return True, f"📘 Tenglama: {text}\n➡️ Yechim: {var} = {sol}"
        else:
            sol = sp.solve(eq)
            return True, f"📘 Ko‘p o‘zgaruvchili tenglama yechimi:\n{sol}"
    except:
        return False, None


def try_solve_expression(text: str):
    t = text.replace("−", "-").replace("^", "**").replace(",", ".")
    try:
        expr = sp.sympify(t)
        simplified = sp.simplify(expr)
        if not simplified.free_symbols:
            return True, f"➡️ Natija: {sp.N(simplified)}"
        return True, f"📘 Soddalashtirish: {sp.pretty(simplified)}"
    except:
        return False, None


def solve_geometry_query(text: str):
    t = text.lower().replace(",", ".")
    # Circle area
    if "aylana" in t and ("maydon" in t or "area" in t):
        m = re.search(r"r\s*=?\s*([0-9\.]+)", t)
        if m:
            r = float(m.group(1))
            area = sp.pi * r * r
            return True, f"📘 Aylana maydoni:\nr = {r}\nS = π·r² = {area.evalf()}"
        m2 = re.search(r"d\s*=?\s*([0-9\.]+)", t)
        if m2:
            d = float(m2.group(1)); r = d/2.0
            area = sp.pi * r * r
            return True, f"📘 Aylana diametri = {d} ⇒ r = {r}\nS = π·r² = {area.evalf()}"

    # Pythagor
    if "pifagor" in t or "pythag" in t:
        nums = re.findall(r"[0-9\.]+", t)
        if len(nums) >= 2:
            a, b = float(nums[0]), float(nums[1])
            c = (a*a + b*b)**0.5
            return True, f"📘 Pifagor:\na = {a}, b = {b}\n➡️ c = {c}"

    # Triangle area (base & height)
    if "uchburchak" in t and ("maydon" in t or "area" in t):
        mb = re.search(r"b\s*=?\s*([0-9\.]+)", t)
        mh = re.search(r"h\s*=?\s*([0-9\.]+)", t)
        if mb and mh:
            b = float(mb.group(1)); h = float(mh.group(1))
            area = 0.5 * b * h
            return True, f"📘 Uchburchak: baza={b}, balandlik={h}\nS = 1/2·b·h = {area}"
    return False, None


def handle_math_query(text: str):
    # 1) Equation
    ok, resp = try_parse_and_solve_equation(text)
    if ok:
        return resp
    # 2) Expression
    ok, resp = try_solve_expression(text)
    if ok:
        return resp
    # 3) Geometry
    ok, resp = solve_geometry_query(text)
    if ok:
        return resp
    # 4) fallback
    try:
        expr = sp.sympify(text)
        simp = sp.simplify(expr)
        out = f"Soddalashtirish: {sp.pretty(simp)}"
        if not simp.free_symbols:
            out += f"\nQiymat: {sp.N(simp)}"
        return out
    except Exception:
        return "Kechirasiz, men bu savolni tushunmadim. Iltimos, masalani aniq va qisqa yozing."

# -----------------------
# Telegram handlers
# -----------------------
@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    # Centered-looking visual not possible in Telegram text; keep concise and friendly
    await message.answer(
        "🤖🌟 Math Helper Botga xush kelibsiz! 🌟🤖\n\n"
        "✏️ Algebra misollarini yozing: 2x+3=13  yoki (3x+2)-(x-4)\n\n"
        "📐 Geometriya uchun yozing: Aylana r=5  yoki Uchburchak a=3 b=4 c=5\n\n"
        "🖼 Rasmni ham tanib, masalani yechib beraman."
    )

@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip()
    # show loading message then replace it with result
    loading = await message.answer("⏳ Qidirilmoqda...")
    result = handle_math_query(text)
    try:
        await loading.edit_text(result)
    except Exception:
        await message.answer(result)

@dp.message(F.photo)
async def handle_photo(message: Message):
    loading = await message.answer("⏳ Rasm o'qilmoqda...")
    file = await bot.get_file(message.photo[-1].file_id)
    tmp_name = f"tmp_img_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, tmp_name)
    txt = ocr_from_image(tmp_name)
    try:
        os.remove(tmp_name)
    except:
        pass
    if not txt:
        return await loading.edit_text("⚠️ OCR bilan matn olinmadi. Iltimos, rasm sifatini yaxshilang va qayta yuboring.")
    result = handle_math_query(txt)
    # show OCR excerpt then result
    out = f"📘 OCR matn: {txt[:900]}\n\n➡️ Natija:\n{result}"
    try:
        await loading.edit_text(out)
    except Exception:
        await message.answer(out)

@dp.message(F.document)
async def block_docs(message: Message):
    mime = message.document.mime_type or ""
    fname = message.document.file_name or ""
    lower = fname.lower()
    if lower.endswith((".exe", ".apk", ".bat", ".cmd", ".msi")):
        await message.answer("❌ Bunday xavfli fayl qabul qilinmaydi.")
        return
    await message.answer("📁 Hozircha fayllar orqali ishlash qo‘llab-quvvatlanmaydi. Iltimos, masalani matn yoki rasm shaklida yuboring.")

# -----------------------
# Run
# -----------------------
async def main():
    print("🤖 Math Helper Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
