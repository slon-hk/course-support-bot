import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models import Course, db, User
from flask import Flask
import requests
from app.services.vector_db import VectorDB
from app.ai import answer_question

logger = logging.getLogger(__name__)

API_BASE_URL = "http://127.0.0.1:5000/api/telegram"  # Адрес вашего Flask API

class CourseBot:
    def __init__(self, app: Flask):
        if not app:
            raise ValueError("Flask application must be provided")

        self.app = app
        self.token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")

        logger.info("Initializing Telegram bot...")
        self.bot = Bot(token=self.token)
        self.dp = Dispatcher()
        self.user_states = {}
        self._register_handlers()
        logger.info("Bot handlers registered successfully")

        # Инициализация VectorDB
        self.vector_db_path = os.path.join(os.getcwd(), "app", "data")
        logger.info(f"Vector DB path: {self.vector_db_path}")

    def _register_handlers(self):
        """Регистрация обработчиков команд"""
        try:
            self.dp.message.register(self.start_handler, Command("start"))
            self.dp.message.register(self.list_courses_handler, Command("courses"))
            self.dp.message.register(self.help_handler, Command("help"))
            self.dp.message.register(self.ask_handler, Command("ask"))  # Обработчик команды /ask
            self.dp.message.register(self.process_question)  # Обработчик для вопросов после выбора курса
            self.dp.callback_query.register(
                self.course_callback_handler,
                lambda c: c.data.startswith('course_')
            )
            self.dp.callback_query.register(
                self.materials_callback_handler,
                lambda c: c.data.startswith('materials_')
            )
            self.dp.callback_query.register(
                self.ask_course_callback_handler,
                lambda c: c.data.startswith('ask_course_')
            )
            self.dp.callback_query.register(
                self.after_question_callback_handler,
                lambda c: c.data in ['end_dialog']
            )
        except Exception as e:
            logger.error(f"Error registering handlers: {e}", exc_info=True)
            raise

    async def start_handler(self, message: types.Message):
        """Обработчик команды /start"""
        try:
            logger.info(f"Start command received from user {message.from_user.id}")
            welcome_text = (
                "👋 Добро пожаловать в бот системы управления курсами!\n\n"
                "Доступные команды:\n"
                "/courses - Просмотр списка курсов\n"
                "/ask - Задать вопрос по материалам курса\n"
                "/help - Помощь и информация"
            )
            await self.bot.send_message(chat_id=message.chat.id, text=welcome_text)
        except Exception as e:
            logger.error(f"Error in start handler: {e}", exc_info=True)
            await self.bot.send_message(chat_id=message.chat.id, text="❌ Произошла ошибка при обработке команды")

    async def ask_handler(self, message: types.Message):
        """Обработчик команды /ask - показывает список курсов для выбора"""
        try:
            with self.app.app_context():
                courses = Course.query.all()
                if not courses:
                    await message.answer("📚 На данный момент нет доступных курсов")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"ask_course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.answer("📚 Выберите курс, по которому хотите задать вопрос:", reply_markup=keyboard)
                logger.info(f"Ask command processed for user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error in ask handler: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка при получении списка курсов")

    async def list_courses_handler(self, message: types.Message):
        """Обработчик команды /courses"""
        try:
            with self.app.app_context():
                courses = Course.query.all()
                if not courses:
                    await message.answer("📚 На данный момент нет доступных курсов")
                    return

                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"📘 {course.title}",
                        callback_data=f"course_{course.id}"
                    )]
                    for course in courses
                ])

                await message.answer("📚 Доступные курсы:", reply_markup=keyboard)
                logger.info(f"Courses listed for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Error in list courses handler: {e}")
            await message.answer("❌ Произошла ошибка при получении списка курсов")

    async def course_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик выбора курса"""
        try:
            course_id = int(callback.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                text = f"📘 {course.title}\n\n{course.description or 'Описание отсутствует'}"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📚 Материалы курса",
                        callback_data=f"materials_{course_id}"
                    )]
                ])

                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in course callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def materials_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик просмотра материалов курса"""
        try:
            course_id = int(callback.data.split('_')[1])
            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                materials = course.materials
                if not materials:
                    await callback.message.edit_text("В этом курсе пока нет материалов")
                    await callback.answer()
                    return

                text = f"📚 Материалы курса {course.title}:\n\n"
                for material in materials:
                    text += f"📝 {material.title}\n"
                    if material.files:
                        for file in material.files:
                            text += f"📎 {file.filename}\n"
                    text += "\n"

                await callback.message.edit_text(text)
                await callback.answer()
        except Exception as e:
            logger.error(f"Error in materials callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def help_handler(self, message: types.Message):
        """Обработчик команды /help"""
        try:
            help_text = (
                "🔍 Справка по использованию бота:\n\n"
                "1️⃣ /start - Начать работу с ботом\n"
                "2️⃣ /courses - Показать список доступных курсов\n"
                "3️⃣ /ask - Задать вопрос по материалам курса\n"
                "4️⃣ /help - Показать это сообщение\n\n"
                "Как задать вопрос:\n"
                "1. Используйте команду /ask\n"
                "2. Выберите курс из списка\n"
                "3. Введите ваш вопрос\n"
                "4. Получите ответ с релевантной информацией\n"
                "5. Продолжайте задавать вопросы"
            )
            await message.reply(help_text)
        except Exception as e:
            logger.error(f"Error in help handler: {e}", exc_info=True)
            await message.reply("❌ Произошла ошибка при обработке команды")

    async def process_question(self, message: types.Message):
        """Обработчик вопросов после выбора курса"""
        try:
            user_id = message.from_user.id
            user_state = self.user_states.get(user_id)

            # Проверяем, ожидаем ли мы вопрос от этого пользователя
            if not user_state or not user_state.get('waiting_for_question'):
                return

            course_id = user_state['course_id']
            question = message.text

            # Создаем клавиатуру с кнопкой завершения
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Завершить диалог", callback_data="end_dialog")]
            ])

            with self.app.app_context():
                # Проверяем существование курса
                course = Course.query.get(course_id)
                if not course:
                    await message.reply("❌ Курс не найден", reply_markup=keyboard)
                    return

                # Поиск ответа с использованием векторной базы данных
                await message.reply("🔍 Ищу ответ на ваш вопрос...")

                try:
                    answer = answer_question(question, self.vector_db_path)

                    if not answer or "К сожалению, я не нашел информации" in answer:
                        await message.reply(
                            "❌ К сожалению, я не нашел релевантной информации по вашему вопросу.\n"
                            "💡 Попробуйте переформулировать вопрос или задать его иначе.\n\n"
                            "Вы можете продолжать задавать вопросы по этому курсу.",
                            reply_markup=keyboard
                        )
                        # Сохраняем состояние для продолжения диалога
                        self.user_states[user_id] = {
                            'waiting_for_question': True,
                            'course_id': course_id
                        }
                        return

                    # Формируем полный ответ с улучшенным форматированием
                    full_response = (
                        f"📚 <b>Результаты поиска по курсу</b>\n"
                        f"<i>{course.title}</i>\n\n"
                        f"❓ <b>Ваш вопрос:</b>\n{question}\n\n"
                        f"🔍 <b>Найденная информация:</b>\n{answer}\n\n"
                        "💡 Вы можете продолжать задавать вопросы по этому курсу\n"
                        "   или нажать кнопку «Завершить диалог» для выхода"
                    )

                    # Отправляем ответ с разбиением на части при необходимости
                    await self.send_split_message(
                        chat_id=message.chat.id,
                        text=full_response,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    logger.info(f"Answered question for user {message.from_user.id} about course {course_id}")

                    # Оставляем пользователя в режиме ожидания следующего вопроса
                    self.user_states[user_id] = {
                        'waiting_for_question': True,
                        'course_id': course_id
                    }

                except Exception as e:
                    logger.error(f"Error processing question: {str(e)}", exc_info=True)
                    await message.reply(
                        "❌ Произошла ошибка при обработке запроса. "
                        "Вы можете попробовать задать вопрос еще раз или завершить диалог.",
                        reply_markup=keyboard
                    )

        except Exception as e:
            user_id = message.from_user.id
            logger.error(f"Error processing question: {e}", exc_info=True)
            await message.reply(
                "❌ Произошла ошибка при обработке вашего вопроса. "
                "Пожалуйста, используйте /ask чтобы начать заново.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Завершить диалог", callback_data="end_dialog")]
                ])
            )
            if user_id:
                self.user_states.pop(user_id, None)

    async def after_question_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик действий после получения ответа на вопрос"""
        try:
            action = callback.data
            user_id = callback.from_user.id

            if action == "end_dialog":
                # Очищаем состояние пользователя и завершаем диалог
                if user_id in self.user_states:
                    self.user_states.pop(user_id)
                await callback.message.edit_text(
                    "✅ Диалог завершен.\n"
                    "Используйте /ask чтобы начать новый диалог с выбором курса."
                )

            await callback.answer()

        except Exception as e:
            logger.error(f"Error in after question callback handler: {e}")
            await callback.answer("❌ Произошла ошибка")

    async def send_split_message(self, chat_id: int, text: str, parse_mode=None, reply_markup=None):
        """Отправка длинного сообщения с разбиением на части"""
        MAX_MESSAGE_LENGTH = 3000

        try:
            if len(text) <= MAX_MESSAGE_LENGTH:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
                return

            parts = []
            while text:
                if len(text) <= MAX_MESSAGE_LENGTH:
                    parts.append(text)
                    break

                split_point = text[:MAX_MESSAGE_LENGTH].rfind('\n')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind('. ')
                if split_point == -1:
                    split_point = text[:MAX_MESSAGE_LENGTH].rfind(' ')
                if split_point == -1:
                    split_point = MAX_MESSAGE_LENGTH

                parts.append(text[:split_point])
                text = text[split_point:].lstrip()

            for i, part in enumerate(parts, 1):
                if i == len(parts):  # Last part
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=part,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
                else:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=part,
                        parse_mode=parse_mode
                    )
                if i < len(parts):
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in send_split_message: {str(e)}")
            await self.bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при отправке сообщения"
            )

    async def start_polling(self):
        """Запуск бота"""
        try:
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def ask_course_callback_handler(self, callback: types.CallbackQuery):
        """Обработчик выбора курса для вопроса"""
        try:
            course_id = int(callback.data.split('_')[2])  # Используем индекс 2, так как формат 'ask_course_ID'
            user_id = callback.from_user.id

            with self.app.app_context():
                course = Course.query.get(course_id)
                if not course:
                    await callback.answer("❌ Курс не найден")
                    return

                # Сохраняем выбранный курс для пользователя
                self.user_states[user_id] = {
                    'waiting_for_question': True,
                    'course_id': course_id
                }

                await callback.message.edit_text(
                    f"📝 Вы выбрали курс: {course.title}\n\n"
                    "Теперь отправьте ваш вопрос в чат.\n"
                    "Вы можете задавать вопросы непрерывно, пока не нажмете кнопку «Завершить диалог»"
                )
                await callback.answer()

        except Exception as e:
            logger.error(f"Error in ask course callback handler: {e}")
            await callback.answer("❌ Произошла ошибка при выборе курса")