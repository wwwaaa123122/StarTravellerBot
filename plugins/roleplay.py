import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai.roleplay import TRIGGHT_KEYWORD, HELP_MESSAGE, on_message, _get_manager
