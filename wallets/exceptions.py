"""
exceptions.py — Custom Domain Exceptions

These exceptions are raised by the service layer (services.py) and caught
by the view layer (views.py) to return appropriate HTTP error responses.
They separate business logic errors from unexpected system errors.
"""


class InsufficientBalanceError(Exception):
    """Raised when a spend request exceeds the wallet's current balance."""

    def __init__(self, current: int, requested: int):
        self.current = current
        self.requested = requested
        super().__init__(f"wallet balance ({current}) is less than requested amount ({requested})")


class WalletNotFoundError(Exception):
    """Raised when a wallet UUID doesn't exist in the database."""
    pass
