import aiosqlite
from typing import Optional, List, Tuple
from datetime import datetime
import logging

from config import DB_PATH, PAGE_SIZE, ALLOWED_ROLES, MAX_SEARCH_LENGTH

logger = logging.getLogger(__name__)

class Database:
    """Класс для обработки всех операций с базой данных."""

    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        """Инициализирует базу данных, создавая таблицы и настройки по умолчанию."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    role TEXT DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                await db.execute("""
                CREATE TABLE IF NOT EXISTS broadcast_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    role_filter TEXT,
                    message TEXT,
                    recipients_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)

                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_users_full_name ON users(full_name)")
                await db.execute("""
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES ('welcome_message', 'Ласкаво просимо до бота! 🎓')
                """)
                await db.commit()
                logger.info("База даних успішно ініціалізована.")
        except Exception as e:
            logger.error(f"Помилка ініціалізації бази даних: {e}")
            raise

    async def add_user(self, user_id: int, username: str, full_name: str) -> bool:
        """Добавляет или обновляет пользователя в базе данных."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                INSERT INTO users (id, username, full_name, last_seen) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_seen = excluded.last_seen
                """, (user_id, username, full_name, datetime.now()))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Помилка додавання користувача {user_id}: {e}")
            return False

    async def set_role(self, user_id: int, role: Optional[str]) -> bool:
        """Устанавливает роль для пользователя."""
        try:
            if role and role not in ALLOWED_ROLES:
                raise ValueError(f"Недійсна роль: {role}")
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Помилка встановлення ролі для {user_id}: {e}")
            return False

    async def get_users(self, offset: int = 0, limit: int = PAGE_SIZE,
                        role: Optional[str] = None) -> List[Tuple]:
        """Получает список пользователей с разбивкой на страницы."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if role and role != "ALL":
                    cur = await db.execute(
                        "SELECT id, full_name, username, role FROM users WHERE role=? "
                        "ORDER BY last_seen DESC LIMIT ? OFFSET ?",
                        (role, limit, offset)
                    )
                else:
                    cur = await db.execute(
                        "SELECT id, full_name, username, role FROM users "
                        "ORDER BY last_seen DESC LIMIT ? OFFSET ?",
                        (limit, offset)
                    )
                return await cur.fetchall()
        except Exception as e:
            logger.error(f"Помилка отримання користувачів: {e}")
            return []

    async def get_users_count(self, role: Optional[str] = None) -> int:
        """Получает общее количество пользователей."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if role and role != "ALL":
                    cur = await db.execute("SELECT COUNT(*) FROM users WHERE role=?", (role,))
                else:
                    cur = await db.execute("SELECT COUNT(*) FROM users")
                row = await cur.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Помилка підрахунку користувачів: {e}")
            return 0

    async def search_users(self, query: str) -> List[Tuple]:
        """Поиск пользователей по идентификатору или имени."""
        try:
            query = query.strip()[:MAX_SEARCH_LENGTH]
            if not query:
                return []
            async with aiosqlite.connect(self.db_path) as db:
                if query.isdigit():
                    cur = await db.execute("SELECT id, full_name, username, role FROM users WHERE id=?", (int(query),))
                else:
                    cur = await db.execute(
                        "SELECT id, full_name, username, role FROM users "
                        "WHERE full_name LIKE ? OR username LIKE ? LIMIT 20",
                        (f"%{query}%", f"%{query}%")
                    )
                return await cur.fetchall()
        except Exception as e:
            logger.error(f"Помилка пошуку користувачів: {e}")
            return []

    async def get_roles_stats(self) -> dict:
        """Получает статистику количества пользователей по ролям."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {role: 0 for role in ALLOWED_ROLES}
                for role in ALLOWED_ROLES:
                    cur = await db.execute("SELECT COUNT(*) FROM users WHERE role=?", (role,))
                    stats[role] = (await cur.fetchone())[0]

                cur = await db.execute("SELECT COUNT(*) FROM users")
                stats["all"] = (await cur.fetchone())[0]
                return stats
        except Exception as e:
            logger.error(f"Помилка отримання статистики ролі: {e}")
            return {role: 0 for role in ALLOWED_ROLES + ["all"]}

    async def get_setting(self, key: str) -> Optional[str]:
        """Извлекает настройку из базы данных."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
                row = await cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Помилка отримання налаштувань {key}: {e}")
            return None

    async def set_setting(self, key: str, value: str) -> bool:
        """Устанавливает настройку в базе данных."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """, (key, value, datetime.now()))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Помилка налаштування {key}: {e}")
            return False

    async def get_users_for_broadcast(self, role: Optional[str] = None) -> List[int]:
        """Получает список идентификаторов пользователей для трансляции."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if role and role != "ALL":
                    cur = await db.execute("SELECT id FROM users WHERE role=?", (role,))
                else:
                    cur = await db.execute("SELECT id FROM users")
                rows = await cur.fetchall()
                return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Помилка отримання користувачів для трансляції: {e}")
            return []

    async def save_broadcast(self, admin_id: int, role_filter: str, message: str, recipients_count: int):
        """Сохраняет запись истории трансляций."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                INSERT INTO broadcast_history (admin_id, role_filter, message, recipients_count, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (admin_id, role_filter, message, recipients_count, datetime.now()))
                await db.commit()
        except Exception as e:
            logger.error(f"Помилка збереження історії трансляцій: {e}")