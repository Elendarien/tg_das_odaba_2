import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from config import ADMINS, MAX_MESSAGE_LENGTH, ALLOWED_ROLES, PAGE_SIZE
from database import Database
from states import SearchUser, EditWelcome, Broadcast
from keyboards import get_admin_panel_kb, get_user_list_kb, get_broadcast_roles_kb

router = Router()
db = Database()
logger = logging.getLogger(__name__)


# Фильтр для проверки, является ли пользователь администратором
def is_admin(user_id: int):
    return user_id in ADMINS


# Вспомогательная функция для избежания дублирования кода
async def _get_admin_panel_text():
    stats = await db.get_roles_stats()
    return (
        "⚙️ Панель адміністратора\n\n"
        f"👤 Загальна к-ть користувачів: {stats['all']}\n"
        f"🎓 Студенти: {stats.get('Студент', 0)}\n"
        f"📚 Абітурієнти: {stats.get('Абітурієнт', 0)}\n"
        f"🧑‍🏫 Викладачі: {stats.get('Викладач', 0)}\n"
        f"👪 Батьки: {stats.get('Батько', 0)}\n"
    )


@router.message(Command("admin"), F.from_user.id.in_(ADMINS))
async def admin_panel(message: types.Message):
    """Отображает главную панель администратора."""
    text = await _get_admin_panel_text()
    keyboard = get_admin_panel_kb()
    await message.answer(text, reply_markup=keyboard)
    logger.info(f"Адміністратор {message.from_user.id} відкрив панель адміністратора.")


@router.callback_query(F.data == "refresh_admin", F.from_user.id.in_(ADMINS))
async def refresh_admin_panel(callback: types.CallbackQuery):
    """Обновляет панель администратора."""
    text = await _get_admin_panel_text()
    keyboard = get_admin_panel_kb()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Оновлено!")
    except TelegramBadRequest:
        await callback.answer()


@router.callback_query(F.data.startswith("manage_users"), F.from_user.id.in_(ADMINS))
async def manage_users(callback: types.CallbackQuery):
    """Обеспечивает управление пользователями и пагинацию."""
    data = callback.data.split(':')
    page = int(data[1])
    role_filter = data[2]

    users = await db.get_users(offset=page * PAGE_SIZE, role=role_filter)
    total_users = await db.get_users_count(role=role_filter)

    text = f"👤 Керування користувачами (Page {page + 1}/{total_users // PAGE_SIZE + 1})\n\n"
    for uid, name, username, urole in users:
        user_info = f"▪️ {name} (ID: `{uid}`)"
        if username:
            user_info += f" (@{username})"
        user_info += f" | Роль: {urole if urole else 'Не встановлено'}"
        text += user_info + "\n"
    if not users:
        text = "За цим фільтром не знайдено користувачів."

    keyboard = get_user_list_kb(users, page, total_users, role_filter)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
        await callback.answer()
    except TelegramBadRequest:
        await callback.answer()


@router.callback_query(F.data.startswith("setrole"), F.from_user.id.in_(ADMINS))
async def set_user_role(callback: types.CallbackQuery, state: FSMContext):
    """Устанавливает роль пользователя."""
    data = callback.data.split(':')
    user_id = int(data[1])
    new_role = data[2]
    page = int(data[3])
    role_filter = data[4]

    if new_role == "NULL":
        new_role_val = None
    else:
        new_role_val = new_role

    success = await db.set_role(user_id, new_role_val)
    if success:
        await callback.answer(f"✅ Роль для користувача {user_id} встановлено на {new_role}")
    else:
        await callback.answer("❌ Не вдалося встановити роль.", show_alert=True)

    # Refresh the user list to show the change
    await state.update_data(page=page, role_filter=role_filter)
    await manage_users(callback)


@router.callback_query(F.data == "search_user", F.from_user.id.in_(ADMINS))
async def start_search_user(callback: types.CallbackQuery, state: FSMContext):
    """Запускает процесс поиска пользователя."""
    await state.set_state(SearchUser.waiting_query)
    await callback.message.edit_text("🔍 Введіть ідентифікатор користувача або частину його імені/імені користувача:")
    await callback.answer()


@router.message(SearchUser.waiting_query, F.from_user.id.in_(ADMINS))
async def process_search_user(message: types.Message, state: FSMContext):
    """Обрабатывает поисковый запрос."""
    query = message.text
    if not query:
        await message.answer("❌ Недійсний запит. Будь ласка, спробуйте ще раз.")
        return

    users = await db.search_users(query)
    text = "🔍 Результати пошуку:\n\n"
    if users:
        for uid, name, username, urole in users:
            user_info = f"▪️ {name} (ID: `{uid}`)"
            if username:
                user_info += f" (@{username})"
            user_info += f" | Роль: {urole if urole else 'Не встановлено'}"
            text += user_info + "\n"
    else:
        text = "❌ За вашим запитом не знайдено користувачів."

    keyboard = get_admin_panel_kb()
    await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.clear()


@router.callback_query(F.data == "edit_welcome", F.from_user.id.in_(ADMINS))
async def start_edit_welcome(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс редактирования приветственного сообщения."""
    await state.set_state(EditWelcome.waiting_text)
    await callback.message.edit_text("✏️ Введіть нове вітальне повідомлення:")
    await callback.answer()


@router.message(EditWelcome.waiting_text, F.from_user.id.in_(ADMINS))
async def process_edit_welcome(message: types.Message, state: FSMContext):
    """Обрабатывает новое приветственное сообщение."""
    new_text = message.text
    if not new_text or len(new_text) > MAX_MESSAGE_LENGTH:
        await message.answer("❌ Недійсне повідомлення. Воно не може бути порожнім або занадто довгим.")
        return

    success = await db.set_setting("welcome_message", new_text)
    if success:
        await message.answer("✅ Вітальне повідомлення успішно оновлено!")
    else:
        await message.answer("❌ Не вдалося оновити вітальне повідомлення.")

    await state.clear()


@router.callback_query(F.data == "broadcast", F.from_user.id.in_(ADMINS))
async def start_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Начинает поток вещания."""
    await state.set_state(Broadcast.select_role)
    await callback.message.edit_text("📢 Виберіть роль користувачів, яким ви хочете надіслати повідомлення:",
                                     reply_markup=get_broadcast_roles_kb())
    await callback.answer()


@router.callback_query(Broadcast.select_role, F.data.startswith("broadcast_role"), F.from_user.id.in_(ADMINS))
async def select_broadcast_role(callback: types.CallbackQuery, state: FSMContext):
    """Выбирает роль для трансляции."""
    role = callback.data.split(':')[1]
    await state.update_data(role_filter=role)
    await state.set_state(Broadcast.waiting_message)
    await callback.message.edit_text(f"✅ Ви обрали роль: {role}\n\n"
                                     f"💬 Тепер введіть повідомлення, яке ви хочете надіслати. "
                                     f"Ви можете використовувати Markdown.")
    await callback.answer()


@router.message(Broadcast.waiting_message, F.from_user.id.in_(ADMINS))
async def waiting_broadcast_message(message: types.Message, state: FSMContext):
    """Обрабатывает широковещательное сообщение."""
    text = message.html_text
    if not text or len(text) > MAX_MESSAGE_LENGTH:
        await message.answer("❌ Недійсне повідомлення. Воно не може бути порожнім або занадто довгим.")
        return

    await state.update_data(message=text)
    await state.set_state(Broadcast.confirm)

    data = await state.get_data()
    role_filter = data.get('role_filter')
    recipients_count = await db.get_users_count(role=role_filter)

    confirm_text = (
        f"📢 Підтвердження трансляції\n\n"
        f"Роль одержувача: {role_filter}\n"
        f"Кількість одержувачів: {recipients_count}\n\n"
        f"Повідомлення:\n\n{text}"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити та надіслати", callback_data="confirm_send_broadcast")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_broadcast")]
    ])

    await message.answer(confirm_text, reply_markup=kb, parse_mode='HTML')


@router.callback_query(Broadcast.confirm, F.data == "confirm_send_broadcast", F.from_user.id.in_(ADMINS))
async def confirm_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждает и отправляет трансляцию."""
    data = await state.get_data()
    role_filter = data.get('role_filter')
    message_text = data.get('message')

    await callback.message.edit_text("⏳ Надсилання трансляції...")
    await callback.answer()

    user_ids = await db.get_users_for_broadcast(role=role_filter)
    sent_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            await asyncio.sleep(0.05)  # Flood control
            await callback.bot.send_message(user_id, message_text, parse_mode='HTML')
            sent_count += 1
        except Exception as e:
            logger.error(f"Не вдалося надіслати повідомлення користувачеві {user_id}: {e}")
            failed_count += 1

    await db.save_broadcast(callback.from_user.id, role_filter, message_text, sent_count)

    await callback.message.edit_text(
        f"✅ Трансляцію успішно надіслано!\n\n"
        f"Надіслано: {sent_count}\n"
        f"Не вдалося: {failed_count}"
    )
    await state.clear()


@router.callback_query(F.data == "cancel_broadcast", F.from_user.id.in_(ADMINS))
async def cancel_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет поток трансляции."""
    await state.clear()
    await callback.message.edit_text("❌ Трансляцію скасовано.")
    await callback.answer()


@router.callback_query(F.data == "back_to_admin", F.from_user.id.in_(ADMINS))
async def back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в панель администратора из любого состояния."""
    await state.clear()
    text = await _get_admin_panel_text()
    keyboard = get_admin_panel_kb()
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except TelegramBadRequest:
        await callback.answer()


@router.callback_query(F.data == "none")
async def none_callback(callback: types.CallbackQuery):
    """Заполнитель обратного вызова для неинтерактивных кнопок."""
    await callback.answer()