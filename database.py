import aiosqlite
import asyncio
import csv
from typing import Optional, Tuple, List, Dict
from config import DB_PATH
from datetime import datetime, timedelta

class Database:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        self._lock = asyncio.Lock()
        self._connection = None

    async def get_connection(self):
        if self._connection is None:
            self._connection = await aiosqlite.connect(self.path)
        return self._connection

    async def close(self):
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def init(self) -> None:
        conn = await self.get_connection()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                registered_at TEXT DEFAULT (datetime('now')),
                in_search INTEGER DEFAULT 0,
                partner_tg_id INTEGER,
                blocked INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0
            )
            """
        )
        await conn.commit()

    async def ensure_user(self, tg_id: int, username: Optional[str]) -> None:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if row is None:
            await conn.execute(
                "INSERT INTO users (tg_id, username) VALUES (?, ?)",
                (tg_id, username),
            )
        else:
            await conn.execute("UPDATE users SET username = ? WHERE tg_id = ?", (username, tg_id))
        await conn.commit()

    async def set_in_search(self, tg_id: int, in_search: bool) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "UPDATE users SET in_search = ? WHERE tg_id = ?",
            (1 if in_search else 0, tg_id),
        )
        await conn.commit()

    async def is_blocked(self, tg_id: int) -> bool:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT blocked FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        return bool(row and row[0])

    async def set_blocked(self, tg_id: int, blocked: bool) -> None:
        conn = await self.get_connection()
        await conn.execute("UPDATE users SET blocked = ? WHERE tg_id = ?", (1 if blocked else 0, tg_id))
        await conn.commit()

    # Убираем метод update_profile с phone_number
    async def update_profile(self, tg_id: int) -> None:
        # Оставляем пустым или удаляем вызовы этого метода
        pass

    async def get_profile(self, tg_id: int) -> Dict[str, Optional[object]]:
        # Возвращаем пустой профиль
        return {}

    async def find_match(self, requester_tg_id: int) -> Optional[int]:
        async with self._lock:
            conn = await self.get_connection()
            cur = await conn.execute("SELECT blocked FROM users WHERE tg_id = ?", (requester_tg_id,))
            row = await cur.fetchone()
            if row and int(row[0]) == 1:
                return None
            
            sql = "SELECT tg_id FROM users WHERE tg_id != ? AND in_search = 1 AND partner_tg_id IS NULL AND (blocked IS NULL OR blocked = 0) LIMIT 1"
            cur = await conn.execute(sql, (requester_tg_id,))
            candidate = await cur.fetchone()
            
            if not candidate:
                return None
            
            partner_tg_id = int(candidate[0])
            
            await conn.execute(
                "UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?",
                (partner_tg_id, requester_tg_id),
            )
            await conn.execute(
                "UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?",
                (requester_tg_id, partner_tg_id),
            )
            await conn.commit()
            return partner_tg_id

    async def set_partner(self, tg_id: int, partner_tg_id: Optional[int]) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "UPDATE users SET partner_tg_id = ? WHERE tg_id = ?",
            (partner_tg_id, tg_id),
        )
        await conn.commit()

    async def get_partner(self, tg_id: int) -> Optional[int]:
        conn = await self.get_connection()
        cur = await conn.execute(
            "SELECT partner_tg_id FROM users WHERE tg_id = ?",
            (tg_id,),
        )
        row = await cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
        return None

    async def clear_dialog(self, tg_a: int, tg_b: int) -> None:
        conn = await self.get_connection()
        await conn.execute(
            "UPDATE users SET partner_tg_id = NULL WHERE tg_id IN (?, ?)",
            (tg_a, tg_b),
        )
        await conn.commit()

    async def end_dialog_for(self, tg_id: int) -> Optional[int]:
        conn = await self.get_connection()
        cur = await conn.execute(
            "SELECT partner_tg_id FROM users WHERE tg_id = ?",
            (tg_id,),
        )
        row = await cur.fetchone()
        if row and row[0] is not None:
            partner = int(row[0])
            await conn.execute(
                "UPDATE users SET partner_tg_id = NULL WHERE tg_id IN (?, ?)",
                (tg_id, partner),
            )
            await conn.commit()
            return partner
        return None

    async def stats(self) -> Tuple[int, int, int]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = int((await cur.fetchone())[0])
        cur = await conn.execute("SELECT COUNT(*) FROM users WHERE in_search = 1")
        searching_users = int((await cur.fetchone())[0])
        cur = await conn.execute("SELECT COUNT(*) FROM users WHERE partner_tg_id IS NOT NULL")
        in_dialog = int((await cur.fetchone())[0])
        active_dialogs = in_dialog // 2
        return total_users, searching_users, active_dialogs

    async def list_searching(self, limit: int = 50) -> List[int]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id FROM users WHERE in_search = 1 ORDER BY registered_at DESC LIMIT ?", (limit,))
        return [int(r[0]) for r in await cur.fetchall()]

    async def list_dialog_pairs(self, limit: int = 50) -> List[Tuple[int, int]]:
        pairs = []
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id, partner_tg_id FROM users WHERE partner_tg_id IS NOT NULL LIMIT ?", (limit * 2,))
        seen = set()
        for tg_id, partner in await cur.fetchall():
            if tg_id in seen or partner is None:
                continue
            pairs.append((int(tg_id), int(partner)))
            seen.add(int(tg_id)); seen.add(int(partner))
        return pairs

    async def get_user(self, tg_id: int) -> Optional[Dict[str, Optional[int]]]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id, username, registered_at, in_search, partner_tg_id, blocked, is_admin FROM users WHERE tg_id = ?", (tg_id,))
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "tg_id": int(row[0]),
            "username": row[1],
            "registered_at": row[2],
            "in_search": int(row[3]) if row[3] is not None else 0,
            "partner_tg_id": int(row[4]) if row[4] is not None else None,
            "blocked": int(row[5]) if row[5] is not None else 0,
            "is_admin": bool(row[6]) if row[6] is not None else False
        }

    async def force_pair(self, a: int, b: int) -> None:
        conn = await self.get_connection()
        await conn.execute("UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?", (b, a))
        await conn.execute("UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?", (a, b))
        await conn.commit()

    async def force_unpair(self, tg_id: int) -> Optional[int]:
        return await self.end_dialog_for(tg_id)

    async def get_all_users(self, limit: int = 100) -> List[tuple]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id, username, registered_at, blocked, is_admin FROM users ORDER BY registered_at DESC LIMIT ?", (limit,))
        return await cur.fetchall()

    async def get_blocked_users(self) -> List[tuple]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id, username, registered_at FROM users WHERE blocked = 1")
        return await cur.fetchall()

    async def get_recent_users(self, days: int = 1) -> int:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT COUNT(*) FROM users WHERE registered_at >= datetime('now', ?)", (f"-{days} days",))
        return (await cur.fetchone())[0]

    async def set_in_search_all(self, in_search: bool):
        conn = await self.get_connection()
        await conn.execute("UPDATE users SET in_search = ?", (1 if in_search else 0,))
        await conn.commit()

    async def set_admin(self, tg_id: int, is_admin: bool) -> None:
        conn = await self.get_connection()
        await conn.execute("UPDATE users SET is_admin = ? WHERE tg_id = ?", (1 if is_admin else 0, tg_id))
        await conn.commit()

    async def get_admins(self) -> List[int]:
        conn = await self.get_connection()
        cur = await conn.execute("SELECT tg_id FROM users WHERE is_admin = 1")
        return [int(row[0]) for row in await cur.fetchall()]