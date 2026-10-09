class BotServiceUnavailableError(RuntimeError):
    public_message = "Bot service is unavailable. Check its configured endpoint and ensure the service is running."
    reason = "bot_service_unavailable"
    retryable = True

    def __init__(self):
        super().__init__(self.public_message)
