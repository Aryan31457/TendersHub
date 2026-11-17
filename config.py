import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv(
    "TARGET_URL",
    "https://etenders.gov.in/eprocure/app?page=FrontEndLatestActiveTenders&service=page",
)
SENDER_EMAIL = os.getenv("ALERT_EMAIL")
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
MAX_PAGES = int(os.getenv("MAX_PAGES", "0"))

# Switch configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-v1"
)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-vl-max")
