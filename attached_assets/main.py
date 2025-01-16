import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_URL = os.getenv('API_URL', '')

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    try:
        response = requests.get(API_URL)
        data = response.json()

        if "error" in data:
            await message.answer("Пользователь не найден!")
            return

        courses = data.get("courses", [])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=course, callback_data=f"course:{course}")]
            for course in courses
        ])

        await message.answer("Список доступных курсов:", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"Ошибка при получении данных: {e}")

@dp.callback_query(F.data.startswith("course:"))
async def handle_course_callback(callback_query: CallbackQuery):
    course_name = callback_query.data.split(":")[1]
    await callback_query.message.answer(
        f"Отлично! Вы выбрали курс {course_name}. Можете задавать любые вопросы по этому курсу."
    )
    await callback_query.answer()

@dp.message()
async def handle_question(message: types.Message):
    # Ответ на любой текстовый вопрос пользователя
    if message.text and not message.text.startswith('/'):
        try:
            await message.answer(
                f"Ваш вопрос: {message.text}\n"
                "Скоро здесь будет реализована интеграция с API для получения ответов."
            )
        except Exception as e:
            await message.answer(f"Произошла ошибка при обработке вопроса: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)  
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())