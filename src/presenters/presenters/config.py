import os


class Config:
    API_KEY = os.getenv("API_KEY")
    SSL_VERIFICATION = os.getenv("SSL_VERIFICATION")
