"""Custom exceptions used across the application."""


class AppError(Exception):
    """Base application exception."""


class ImageReadError(AppError):
    """Raised when an image cannot be opened or parsed safely."""


class ConversionError(AppError):
    """Raised when a conversion cannot be completed."""
