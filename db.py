import aiosqlite

import asyncio

import csv

from typing import Optional, Tuple, List, Dict, Set





def _normalize_interests(raw: Optional[str]) -> Set[str]:

	if not raw:

		return set()

	parts = [p.strip().lower() for p in str(raw).split(",")]

	return {p for p in parts if p}





class Database:

	def __init__(self, path: str = "anonimchat.db") -> None:

		self.path = path

		self._lock = asyncio.Lock()



	async def init(self) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute(

				"""

				CREATE TABLE IF NOT EXISTS users (

					id INTEGER PRIMARY KEY AUTOINCREMENT,

					tg_id INTEGER UNIQUE NOT NULL,

					username TEXT,

					registered_at TEXT DEFAULT (datetime('now')),

					in_search INTEGER DEFAULT 0,

					partner_tg_id INTEGER

				)

				"""

			)

			# Best-effort migrations

			for sql in [

				"ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0",

				"ALTER TABLE users ADD COLUMN gender TEXT",

				"ALTER TABLE users ADD COLUMN seeking_gender TEXT",

				"ALTER TABLE users ADD COLUMN age INTEGER",

				"ALTER TABLE users ADD COLUMN interests TEXT",

			]:

				try:

					await db.execute(sql)

				except Exception:

					pass

			await db.commit()



	async def ensure_user(self, tg_id: int, username: Optional[str]) -> None:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))

			row = await cur.fetchone()

			if row is None:

				await db.execute(

					"INSERT INTO users (tg_id, username) VALUES (?, ?)",

					(tg_id, username),

				)

				await db.commit()

			else:

				await db.execute("UPDATE users SET username = ? WHERE tg_id = ?", (username, tg_id))

				await db.commit()



	async def set_in_search(self, tg_id: int, in_search: bool) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute(

				"UPDATE users SET in_search = ? WHERE tg_id = ?",

				(1 if in_search else 0, tg_id),

			)

			await db.commit()



	async def is_blocked(self, tg_id: int) -> bool:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT blocked FROM users WHERE tg_id = ?", (tg_id,))

			row = await cur.fetchone()

			return bool(row and row[0])



	async def set_blocked(self, tg_id: int, blocked: bool) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute("UPDATE users SET blocked = ? WHERE tg_id = ?", (1 if blocked else 0, tg_id))

			await db.commit()



	async def update_profile(self, tg_id: int, *, gender: Optional[str] = None, seeking_gender: Optional[str] = None, age: Optional[int] = None, interests: Optional[str] = None) -> None:

		sets = []

		vals: List[object] = []

		if gender is not None:

			sets.append("gender = ?"); vals.append(gender)

		if seeking_gender is not None:

			sets.append("seeking_gender = ?"); vals.append(seeking_gender)

		if age is not None:

			sets.append("age = ?"); vals.append(age)

		if interests is not None:

			sets.append("interests = ?"); vals.append(interests)

		if not sets:

			return

		vals.append(tg_id)

		async with aiosqlite.connect(self.path) as db:

			await db.execute(f"UPDATE users SET {', '.join(sets)} WHERE tg_id = ?", vals)

			await db.commit()



	async def get_profile(self, tg_id: int) -> Dict[str, Optional[object]]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT gender, seeking_gender, age, interests FROM users WHERE tg_id = ?", (tg_id,))

			row = await cur.fetchone()

			if not row:

				return {"gender": None, "seeking_gender": None, "age": None, "interests": None}

			return {"gender": row[0], "seeking_gender": row[1], "age": row[2], "interests": row[3]}



	async def find_match(self, requester_tg_id: int) -> Optional[int]:

		async with self._lock:

			async with aiosqlite.connect(self.path) as db:

				# Skip blocked requester and get preferences

				cur = await db.execute("SELECT blocked, seeking_gender, interests FROM users WHERE tg_id = ?", (requester_tg_id,))

				row = await cur.fetchone()

				if row and int(row[0]) == 1:

					return None

				req_seek = row[1] if row else None

				req_interests = _normalize_interests(row[2] if row else None)

				params: List[object] = [requester_tg_id]

				where = [

					"tg_id != ?",

					"in_search = 1",

					"(partner_tg_id IS NULL)",

					"(blocked IS NULL OR blocked = 0)",

				]

				if req_seek and req_seek in ("male", "female"):

					where.append("gender = ?")

					params.append(req_seek)

				sql = f"SELECT tg_id, interests FROM users WHERE {' AND '.join(where)} ORDER BY registered_at DESC LIMIT 50"

				cur = await db.execute(sql, tuple(params))

				candidates = await cur.fetchall()

				if not candidates:

					return None

				# Score by shared interests count

				best_id = None

				best_score = -1

				for cand_id, cand_interests in candidates:

					cand_set = _normalize_interests(cand_interests)

					score = len(req_interests & cand_set) if req_interests else 0

					if score > best_score:

						best_score = score

						best_id = int(cand_id)

				# Fallback to first if none

				partner_tg_id = best_id if best_id is not None else int(candidates[0][0])

				await db.execute(

					"UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?",

					(partner_tg_id, requester_tg_id),

				)

				await db.execute(

					"UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?",

					(requester_tg_id, partner_tg_id),

				)

				await db.commit()

				return partner_tg_id



	async def set_partner(self, tg_id: int, partner_tg_id: Optional[int]) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute(

				"UPDATE users SET partner_tg_id = ? WHERE tg_id = ?",

				(partner_tg_id, tg_id),

			)

			await db.commit()



	async def get_partner(self, tg_id: int) -> Optional[int]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute(

				"SELECT partner_tg_id FROM users WHERE tg_id = ?",

				(tg_id,),

			)

			row = await cur.fetchone()

			if row and row[0] is not None:

				return int(row[0])

			return None



	async def clear_dialog(self, tg_a: int, tg_b: int) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute(

				"UPDATE users SET partner_tg_id = NULL WHERE tg_id IN (?, ?)",

				(tg_a, tg_b),

			)

			await db.commit()



	async def end_dialog_for(self, tg_id: int) -> Optional[int]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute(

				"SELECT partner_tg_id FROM users WHERE tg_id = ?",

				(tg_id,),

			)

			row = await cur.fetchone()

			if row and row[0] is not None:

				partner = int(row[0])

				await db.execute(

					"UPDATE users SET partner_tg_id = NULL WHERE tg_id IN (?, ?)",

					(tg_id, partner),

				)

				await db.commit()

				return partner

			return None



	async def stats(self) -> Tuple[int, int, int]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT COUNT(*) FROM users")

			total_users = int((await cur.fetchone())[0])

			cur = await db.execute("SELECT COUNT(*) FROM users WHERE in_search = 1")

			searching_users = int((await cur.fetchone())[0])

			cur = await db.execute("SELECT COUNT(*) FROM users WHERE partner_tg_id IS NOT NULL")

			in_dialog = int((await cur.fetchone())[0])

			active_dialogs = in_dialog // 2

			return total_users, searching_users, active_dialogs



	async def list_searching(self, limit: int = 50) -> List[int]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT tg_id FROM users WHERE in_search = 1 ORDER BY registered_at DESC LIMIT ?", (limit,))

			return [int(r[0]) for r in await cur.fetchall()]



	async def list_dialog_pairs(self, limit: int = 50) -> List[Tuple[int, int]]:

		pairs: List[Tuple[int, int]] = []

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT tg_id, partner_tg_id FROM users WHERE partner_tg_id IS NOT NULL LIMIT ?", (limit * 2,))

			seen = set()

			for tg_id, partner in await cur.fetchall():

				if tg_id in seen or partner is None:

					continue

				pairs.append((int(tg_id), int(partner)))

				seen.add(int(tg_id)); seen.add(int(partner))

		return pairs



	async def get_user(self, tg_id: int) -> Optional[Dict[str, Optional[int]]]:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT tg_id, username, registered_at, in_search, partner_tg_id, blocked, gender, seeking_gender, age, interests FROM users WHERE tg_id = ?", (tg_id,))

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

				"gender": row[6],

				"seeking_gender": row[7],

				"age": row[8],

				"interests": row[9],

			}



	async def force_pair(self, a: int, b: int) -> None:

		async with aiosqlite.connect(self.path) as db:

			await db.execute("UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?", (b, a))

			await db.execute("UPDATE users SET partner_tg_id = ?, in_search = 0 WHERE tg_id = ?", (a, b))

			await db.commit()



	async def force_unpair(self, tg_id: int) -> Optional[int]:

		return await self.end_dialog_for(tg_id)



	async def export_csv(self, file_path: str = "export_users.csv") -> str:

		async with aiosqlite.connect(self.path) as db:

			cur = await db.execute("SELECT tg_id, username, registered_at, in_search, partner_tg_id, blocked, gender, seeking_gender, age, interests FROM users ORDER BY id DESC")

			rows = await cur.fetchall()

		with open(file_path, "w", newline="", encoding="utf-8") as f:

			writer = csv.writer(f)

			writer.writerow(["tg_id", "username", "registered_at", "in_search", "partner_tg_id", "blocked", "gender", "seeking_gender", "age", "interests"])

			for r in rows:

				writer.writerow(r)

		return file_path

