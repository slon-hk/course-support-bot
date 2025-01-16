import asyncio
import logging
from app import create_app
from app.bot.bot import CourseBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    try:
        # Создаем Flask приложение
        app = create_app()

        # Создаем и запускаем бота
        bot = CourseBot(app)
        logger.info("Bot instance created successfully")
        await bot.start_polling()

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error in bot execution: {e}")