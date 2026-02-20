class InsufficientBalanceError(Exception):
    def __init__(self, current: int, requested: int):
        self.current = current
        self.requested = requested
        super().__init__(f"wallet balance ({current}) is less than requested amount ({requested})")


class WalletNotFoundError(Exception):
    pass
