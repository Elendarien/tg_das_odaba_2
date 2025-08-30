from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, List, Tuple
from config import ALLOWED_ROLES, PAGE_SIZE

def get_admin_panel_kb() -> InlineKeyboardMarkup:
    """Возвращает основную клавиатуру панели администратора."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Змінити вітальне повідомлення", callback_data="edit_welcome")],
        [InlineKeyboardButton(text="👤 Керування користувачами", callback_data="manage_users:0:ALL")],
        [InlineKeyboardButton(text="🔍 Знайти користувача", callback_data="search_user")],
        [InlineKeyboardButton(text="📤 Надіслати розсилку", callback_data="broadcast")],
        [InlineKeyboardButton(text="🔄 Оновити", callback_data="refresh_admin")]
    ])

def get_broadcast_roles_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для выбора роли вещания."""
    buttons = [[InlineKeyboardButton(text="📢 Усі користувачі", callback_data="broadcast_role:ALL")]]
    for role in ALLOWED_ROLES:
        buttons.append([InlineKeyboardButton(text=f"🎓 {role}", callback_data=f"broadcast_role:{role}")])
    buttons.append([InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_broadcast")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_list_kb(users: List[Tuple], page: int, total_users: int, current_filter: str) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для управления пользователями с пагинацией."""
    keyboard = []

    for uid, name, username, urole in users:
        role_buttons = []
        for btn_role in ALLOWED_ROLES:
            role_buttons.append(
                InlineKeyboardButton(
                    text=f"{'✅ ' if urole == btn_role else ''}{btn_role}",
                    callback_data=f"setrole:{uid}:{btn_role}:{page}:{current_filter}"
                )
            )
        keyboard.append(role_buttons)
        keyboard.append([InlineKeyboardButton(text="❌ Видалити роль", callback_data=f"setrole:{uid}:NULL:{page}:{current_filter}")])
        keyboard.append([InlineKeyboardButton(text="—" * 20, callback_data="none")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Попередня", callback_data=f"manage_users:{page - 1}:{current_filter}"))
    if (page + 1) * PAGE_SIZE < total_users:
        nav.append(InlineKeyboardButton(text="▶️ Наступна", callback_data=f"manage_users:{page + 1}:{current_filter}"))
    if nav:
        keyboard.append(nav)

    filters = [InlineKeyboardButton(text=f"{'🔹 ' if current_filter == 'ALL' else ''}All", callback_data="manage_users:0:ALL")]
    for filter_role in ALLOWED_ROLES:
        filters.append(InlineKeyboardButton(text=f"{'🔹 ' if current_filter == filter_role else ''}{filter_role[:3]}", callback_data=f"manage_users:0:{filter_role}"))
    keyboard.append(filters)

    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)