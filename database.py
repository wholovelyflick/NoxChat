import aiohttp
import json
import base64
import asyncio
from typing import Optional, Tuple, List, Dict, Set
from config import DB_PATH
from datetime import datetime

class Database:
    def __init__(self, github_token: str = "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", 
                 repo_owner: str = "wholovelyflick", 
                 repo_name: str = "NoxChat",
                 db_file: str = "db.txt") -> None:
        self.github_token = github_token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.db_file = db_file
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
        self._data = {
            "users": {},
            "dialogs": {},
            "reports": {},
            "reactions": {}
        }
        self._lock = asyncio.Lock()

    def _get_current_timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def _get_file_content(self) -> Dict:
        """Получить содержимое файла с GitHub"""
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/{self.db_file}", headers=headers) as response:
                    if response.status == 200:
                        content = await response.json()
                        file_content = base64.b64decode(content['content']).decode('utf-8')
                        return json.loads(file_content) if file_content.strip() else self._data.copy()
                    else:
                        return self._data.copy()
        except Exception:
            return self._data.copy()

    async def _update_file_content(self, content: Dict) -> bool:
        """Обновить содержимое файла на GitHub"""
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Получаем текущий sha для обновления
        sha = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/{self.db_file}", headers=headers) as response:
                    if response.status == 200:
                        current_file = await response.json()
                        sha = current_file['sha']
        except Exception:
            pass

        # Подготавливаем данные для отправки
        file_content = json.dumps(content, ensure_ascii=False, indent=2)
        encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')
        
        data = {
            "message": f"Update database {self._get_current_timestamp()}",
            "content": encoded_content,
            "branch": "main"
        }
        
        if sha:
            data["sha"] = sha

        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(f"{self.base_url}/{self.db_file}", headers=headers, json=data) as response:
                    return response.status in [200, 201]
        except Exception:
            return False

    async def init(self) -> None:
        """Инициализация базы данных"""
        self._data = await self._get_file_content()

    async def ensure_user(self, tg_id: int, username: Optional[str]) -> None:
        """Создать пользователя если не существует"""
        user_id = str(tg_id)
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {
                "tg_id": tg_id,
                "username": username,
                "phone_number": None,
                "registered_at": self._get_current_timestamp(),
                "in_search": False,
                "partner_tg_id": None,
                "blocked": False,
                "is_admin": False,
                "gender": None,
                "seeking_gender": None,
                "age": None,
                "interests": None
            }
            await self._update_file_content(self._data)
        else:
            # Обновляем username если изменился
            if self._data["users"][user_id]["username"] != username:
                self._data["users"][user_id]["username"] = username
                await self._update_file_content(self._data)

    async def set_in_search(self, tg_id: int, in_search: bool) -> None:
        user_id = str(tg_id)
        if user_id in self._data["users"]:
            self._data["users"][user_id]["in_search"] = in_search
            await self._update_file_content(self._data)

    async def is_blocked(self, tg_id: int) -> bool:
        user_id = str(tg_id)
        return self._data["users"].get(user_id, {}).get("blocked", False)

    async def set_blocked(self, tg_id: int, blocked: bool) -> None:
        user_id = str(tg_id)
        if user_id in self._data["users"]:
            self._data["users"][user_id]["blocked"] = blocked
            await self._update_file_content(self._data)

    async def update_profile(self, tg_id: int, *, gender: Optional[str] = None, 
                           seeking_gender: Optional[str] = None, age: Optional[int] = None, 
                           interests: Optional[str] = None, phone_number: Optional[str] = None) -> None:
        user_id = str(tg_id)
        if user_id in self._data["users"]:
            if gender is not None:
                self._data["users"][user_id]["gender"] = gender
            if seeking_gender is not None:
                self._data["users"][user_id]["seeking_gender"] = seeking_gender
            if age is not None:
                self._data["users"][user_id]["age"] = age
            if interests is not None:
                self._data["users"][user_id]["interests"] = interests
            if phone_number is not None:
                self._data["users"][user_id]["phone_number"] = phone_number
            
            await self._update_file_content(self._data)

    async def get_profile(self, tg_id: int) -> Dict[str, Optional[object]]:
        user_id = str(tg_id)
        user = self._data["users"].get(user_id, {})
        return {
            "gender": user.get("gender"),
            "seeking_gender": user.get("seeking_gender"),
            "age": user.get("age"),
            "interests": user.get("interests"),
            "phone_number": user.get("phone_number")
        }

    def _normalize_interests(self, raw: Optional[str]) -> Set[str]:
        if not raw:
            return set()
        parts = [p.strip().lower() for p in str(raw).split(",")]
        return {p for p in parts if p}

    async def find_match(self, requester_tg_id: int) -> Optional[int]:
        async with self._lock:
            requester_id = str(requester_tg_id)
            requester = self._data["users"].get(requester_id, {})
            
            if requester.get("blocked", False):
                return None
            
            req_seek = requester.get("seeking_gender")
            req_interests = self._normalize_interests(requester.get("interests"))
            
            candidates = []
            for user_id, user in self._data["users"].items():
                if (user_id != requester_id and 
                    user.get("in_search", False) and 
                    not user.get("blocked", False) and 
                    user.get("partner_tg_id") is None):
                    
                    # Проверка по полу если указано
                    if req_seek and req_seek in ("male", "female"):
                        if user.get("gender") != req_seek:
                            continue
                    
                    candidates.append((int(user_id), user.get("interests")))
            
            if not candidates:
                return None
            
            # Сортировка по интересам
            best_id = None
            best_score = -1
            for cand_id, cand_interests in candidates:
                cand_set = self._normalize_interests(cand_interests)
                score = len(req_interests & cand_set) if req_interests else 0
                if score > best_score:
                    best_score = score
                    best_id = cand_id
            
            partner_tg_id = best_id if best_id is not None else candidates[0][0]
            
            # Обновляем обоих пользователей
            self._data["users"][requester_id]["partner_tg_id"] = partner_tg_id
            self._data["users"][requester_id]["in_search"] = False
            self._data["users"][str(partner_tg_id)]["partner_tg_id"] = requester_tg_id
            self._data["users"][str(partner_tg_id)]["in_search"] = False
            
            await self._update_file_content(self._data)
            return partner_tg_id

    async def set_partner(self, tg_id: int, partner_tg_id: Optional[int]) -> None:
        user_id = str(tg_id)
        if user_id in self._data["users"]:
            self._data["users"][user_id]["partner_tg_id"] = partner_tg_id
            await self._update_file_content(self._data)

    async def get_partner(self, tg_id: int) -> Optional[int]:
        user_id = str(tg_id)
        return self._data["users"].get(user_id, {}).get("partner_tg_id")

    async def clear_dialog(self, tg_a: int, tg_b: int) -> None:
        user_a = str(tg_a)
        user_b = str(tg_b)
        
        if user_a in self._data["users"]:
            self._data["users"][user_a]["partner_tg_id"] = None
        if user_b in self._data["users"]:
            self._data["users"][user_b]["partner_tg_id"] = None
        
        await self._update_file_content(self._data)

    async def end_dialog_for(self, tg_id: int) -> Optional[int]:
        user_id = str(tg_id)
        user = self._data["users"].get(user_id, {})
        partner_tg_id = user.get("partner_tg_id")
        
        if partner_tg_id is not None:
            self._data["users"][user_id]["partner_tg_id"] = None
            partner_id = str(partner_tg_id)
            if partner_id in self._data["users"]:
                self._data["users"][partner_id]["partner_tg_id"] = None
            
            await self._update_file_content(self._data)
            return partner_tg_id
        return None

    async def stats(self) -> Tuple[int, int, int]:
        total_users = len(self._data["users"])
        searching_users = sum(1 for user in self._data["users"].values() if user.get("in_search", False))
        in_dialog = sum(1 for user in self._data["users"].values() if user.get("partner_tg_id") is not None)
        active_dialogs = in_dialog // 2
        return total_users, searching_users, active_dialogs

    async def list_searching(self, limit: int = 50) -> List[int]:
        searching = []
        for user_id, user in self._data["users"].items():
            if user.get("in_search", False) and user.get("partner_tg_id") is None:
                searching.append(int(user_id))
                if len(searching) >= limit:
                    break
        return searching

    async def list_dialog_pairs(self, limit: int = 50) -> List[Tuple[int, int]]:
        pairs = []
        seen = set()
        
        for user_id, user in self._data["users"].items():
            partner_tg_id = user.get("partner_tg_id")
            if (partner_tg_id is not None and 
                int(user_id) not in seen and 
                partner_tg_id not in seen):
                
                pairs.append((int(user_id), partner_tg_id))
                seen.add(int(user_id))
                seen.add(partner_tg_id)
                
                if len(pairs) >= limit:
                    break
        
        return pairs

    async def get_user(self, tg_id: int) -> Optional[Dict[str, Optional[object]]]:
        user_id = str(tg_id)
        user = self._data["users"].get(user_id)
        if not user:
            return None
        
        return {
            "tg_id": user["tg_id"],
            "username": user.get("username"),
            "phone_number": user.get("phone_number"),
            "registered_at": user.get("registered_at"),
            "in_search": user.get("in_search", False),
            "partner_tg_id": user.get("partner_tg_id"),
            "blocked": user.get("blocked", False),
            "is_admin": user.get("is_admin", False),
            "gender": user.get("gender"),
            "seeking_gender": user.get("seeking_gender"),
            "age": user.get("age"),
            "interests": user.get("interests")
        }

    async def force_pair(self, a: int, b: int) -> None:
        user_a = str(a)
        user_b = str(b)
        
        if user_a in self._data["users"]:
            self._data["users"][user_a]["partner_tg_id"] = b
            self._data["users"][user_a]["in_search"] = False
        if user_b in self._data["users"]:
            self._data["users"][user_b]["partner_tg_id"] = a
            self._data["users"][user_b]["in_search"] = False
        
        await self._update_file_content(self._data)

    async def force_unpair(self, tg_id: int) -> Optional[int]:
        return await self.end_dialog_for(tg_id)

    async def get_all_users(self, limit: int = 100) -> List[tuple]:
        users = []
        for user_id, user in list(self._data["users"].items())[:limit]:
            users.append((
                user["tg_id"],
                user.get("username"),
                user.get("phone_number"),
                user.get("registered_at"),
                user.get("blocked", False),
                user.get("is_admin", False)
            ))
        return users

    async def get_blocked_users(self) -> List[tuple]:
        blocked = []
        for user_id, user in self._data["users"].items():
            if user.get("blocked", False):
                blocked.append((
                    user["tg_id"],
                    user.get("username"),
                    user.get("phone_number"),
                    user.get("registered_at")
                ))
        return blocked

    async def get_recent_users(self, days: int = 1) -> int:
        count = 0
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for user in self._data["users"].values():
            try:
                reg_date = datetime.strptime(user.get("registered_at", ""), "%Y-%m-%d %H:%M:%S")
                if reg_date.timestamp() >= cutoff_date:
                    count += 1
            except:
                continue
        
        return count

    async def set_admin(self, tg_id: int, is_admin: bool) -> None:
        user_id = str(tg_id)
        if user_id in self._data["users"]:
            self._data["users"][user_id]["is_admin"] = is_admin
            await self._update_file_content(self._data)

    async def get_admins(self) -> List[int]:
        admins = []
        for user in self._data["users"].values():
            if user.get("is_admin", False):
                admins.append(user["tg_id"])
        return admins

    async def export_csv(self, file_path: str = "export_users.csv") -> str:
        import csv
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tg_id", "username", "registered_at", "in_search", "partner_tg_id", "blocked", "gender", "seeking_gender", "age", "interests"])
            for user in self._data["users"].values():
                writer.writerow([
                    user["tg_id"],
                    user.get("username"),
                    user.get("registered_at"),
                    user.get("in_search", False),
                    user.get("partner_tg_id"),
                    user.get("blocked", False),
                    user.get("gender"),
                    user.get("seeking_gender"),
                    user.get("age"),
                    user.get("interests")
                ])
        return file_path

    async def close(self) -> None:
        # Сохраняем данные при закрытии
        await self._update_file_content(self._data)