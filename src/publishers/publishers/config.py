import os


class Config:
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_SEND = os.getenv("EMAIL_SEND")
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION")
