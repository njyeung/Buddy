from datetime import datetime
from pathlib import Path
import platform

BASE_PATH = Path(__file__).parent
OS_NAME = platform.system()
MAX_FUNCTION_CALL_DEPTH = 2
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
SUMMARY_TRIGGER_CHAR_COUNT = 4000
NUM_RECENT_MESSAGES_TO_KEEP = 7