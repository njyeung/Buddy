from datetime import datetime
from pathlib import Path
import platform

BASE_PATH = Path(__file__).parent
OS_NAME = platform.system()
MAX_FUNCTION_CALL_DEPTH = 5
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
SUMMARY_TRIGGER_CHAR_COUNT = 5000
NUM_RECENT_MESSAGES_TO_KEEP = 5
MASTER_MODEL="gpt-4.1-mini"
SLAVE_MODEL="gpt-4.1-nano"