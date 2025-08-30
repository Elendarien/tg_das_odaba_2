import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

router = Router()
db = Database()
logger = logging.getLogger(__name__)

class SaveUserMiddleware:
    """Промежуточное программное обеспечение для сохранения информации о пользователе в каждом сообщении."""
    async def __call__(self, handler, event, data):
        if event.from_user and not event.from_user.is_bot:
            await db.add_user(event.from_user.id, event.from_user.username, event.from_user.full_name)
        return await handler(event, data)

@router.message(Command("start"))
async def start_command(message: types.Message):
    """Обрабатывает команду /start."""
    welcome = await db.get_setting("welcome_message")
    if not welcome:
        welcome = "Ласкаво просимо до бота! 🎓"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Інформація", callback_data="info")],
        [InlineKeyboardButton(text="📞 Контакти", callback_data="contacts")]
    ])

    await message.answer(welcome, reply_markup=keyboard)
    logger.info(f"Новий користувач: {message.from_user.id} - {message.from_user.full_name}")

@router.message(Command("help"))
async def help_command(message: types.Message):
    """Обрабатывает команду /help."""
    text = (
        "📚 Доступні команди:\n\n"
        "/start - Почати\n"
        "/help - Отримати допомогу\n"
    )
    await message.answer(text)

@router.callback_query(F.data == "info")
async def show_info(callback: types.CallbackQuery):
    """Отображает информацию о боте."""
    await callback.message.edit_text("Цей бот призначений для управління спільнотою.")
    await callback.answer()

@router.callback_query(F.data == "contacts")
async def show_contacts(callback: types.CallbackQuery):
    """Отображает контактную информацию."""
    #await callback.message.edit_text("Ви можете зв'язатися з нами через @ваше_контактне_ім'я_користувача")
    #await callback.answer()
    text = (
        "📞 Контакти\n\n"
        "📧 Email: info@university.edu\n"
        "📱 Телефон: +380 XX XXX XX XX\n"
        "🌐 Сайт: www.university.edu\n\n"
        "Графік роботи:\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб-Нд: вихідні"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery):
    """Возврат в стартовое меню."""
    welcome = await db.get_setting("welcome_message")
    if not welcome:
        welcome = "Ласкаво просимо до бота! 🎓"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Інформація", callback_data="info")],
        [InlineKeyboardButton(text="📞 Контакти", callback_data="contacts")]
    ])

    await callback.message.edit_text(welcome, reply_markup=keyboard)
    await callback.answer()