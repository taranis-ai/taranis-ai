class ConnectorError(RuntimeError):
    def __init__(self, public_message: str, reason: str):
        super().__init__(public_message)
        self.public_message = public_message
        self.reason = reason
