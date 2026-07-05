VERSION_NAME = "3.1 - Next Release"


class BotContext:
    """Bot 运行状态（本地版，无父项目依赖）"""

    def __init__(self):
        self.EnableNetwork = "Ds"
        self.user_lists = {}
        self.stop_working = False
