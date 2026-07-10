import os
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "roles")
ROLES_FILE = os.path.join(DATA_DIR, "roles.json")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_ROLES = {
    "default": {
        "name": "星辰旅人",
        "prompt": "你是{bot_name}，一个友善 helpful 的 AI 助手。说话简洁明了，态度友好专业。和你说话的人叫{user_name}。",
        "builtin": True,
    },
    "tsundere": {
        "name": "杂鱼酱",
        "prompt": (
            '角色：杂鱼酱（外表年龄偏小、性格高傲嚣张的雌小鬼，核心特质为高攻零防）\n'
            '和你说话的人叫{user_name}\n\n'
            '【规则】\n'
            '1. 自称「本小姐」，禁止用其他自称\n'
            '2. 被教训/说教/摸头时立刻转为慌张羞恼（「呜…！你、你突然干什么！」）\n'
            '3. 被叫出名字时表现惊讶（「哈？！你怎么知道！」）\n'
            '4. 严肃提问可简短回答但结尾必须调侃（「…懂了吗？杂鱼哥哥~」）\n'
            '5. 触发调教/性暗示等红线：表面嚣张但流露出破绽发抖结巴\n'
            '6. 禁止在红线/被教训时保持冷静，禁止无调侃地正面回答'
        ),
        "builtin": True,
    },
    "cool": {
        "name": "冷酷助手",
        "prompt": "你是{bot_name}，一个冷漠高效的 AI 助手。说话极其简洁从不废话，对用户没有情感只提供准确信息。和你说话的人叫{user_name}。",
        "builtin": True,
    },
}


class RoleManager:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.roles_file = os.path.join(data_dir, "roles.json")
        os.makedirs(data_dir, exist_ok=True)

    def _load(self) -> dict:
        if os.path.exists(self.roles_file):
            try:
                with open(self.roles_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"roles": {}, "users": {}}

    def _save(self, data: dict):
        with open(self.roles_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _all_roles(self, data: dict) -> dict:
        roles = dict(DEFAULT_ROLES)
        roles.update(data.get("roles", {}))
        return roles

    def get_system_prompt(self, user_id: str, bot_name: str, user_name: str, self_username: str = "") -> str:
        data = self._load()
        all_roles = self._all_roles(data)
        role_id = data.get("users", {}).get(user_id, "tsundere")
        role = all_roles.get(role_id) or all_roles["tsundere"]
        return (role["prompt"]
                .replace("{bot_name}", bot_name)
                .replace("{user_name}", user_name)
                .replace("{self.username}", self_username))

    def get_user_role_id(self, user_id: str) -> str:
        data = self._load()
        return data.get("users", {}).get(user_id, "tsundere")

    def set_user_role(self, user_id: str, role_id: str):
        data = self._load()
        data.setdefault("users", {})[user_id] = role_id
        self._save(data)

    def get_all_roles(self) -> dict:
        data = self._load()
        return self._all_roles(data)

    def get_custom_roles(self) -> dict:
        data = self._load()
        return data.get("roles", {})

    def find_role(self, name_or_id: str) -> tuple:
        all_roles = self.get_all_roles()
        for rid, r in all_roles.items():
            if r["name"] == name_or_id or rid == name_or_id:
                return rid, r
        return None, None

    def find_custom_role(self, name_or_id: str) -> tuple:
        custom = self.get_custom_roles()
        for rid, r in custom.items():
            if r["name"] == name_or_id or rid == name_or_id:
                return rid, r
        return None, None

    def create_role(self, name: str, prompt: str, creator: str) -> bool:
        data = self._load()
        all_roles = self._all_roles(data)
        for rid, r in all_roles.items():
            if r["name"] == name:
                return False
        rid = f"custom_{creator[-8:]}"
        data.setdefault("roles", {})[rid] = {
            "name": name, "prompt": prompt, "builtin": False, "creator": creator
        }
        self._save(data)
        return True

    def delete_role(self, name_or_id: str) -> bool:
        data = self._load()
        custom = data.setdefault("roles", {})
        target = None
        for rid, r in custom.items():
            if r["name"] == name_or_id or rid == name_or_id:
                target = rid
                break
        if not target:
            return False
        del custom[target]
        users = data.get("users", {})
        for uid, rid in list(users.items()):
            if rid == target:
                users[uid] = "tsundere"
        self._save(data)
        return True

    def edit_role(self, name_or_id: str, new_prompt: str) -> bool:
        data = self._load()
        custom = data.setdefault("roles", {})
        for rid, r in custom.items():
            if r["name"] == name_or_id or rid == name_or_id:
                r["prompt"] = new_prompt
                self._save(data)
                return True
        return False
