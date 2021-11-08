import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_SEND = os.getenv("EMAIL_SEND")
