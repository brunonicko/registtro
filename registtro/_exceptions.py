class RegisttroException(Exception):
    """Base registtro exception."""


class EntryNotFoundError(RegisttroException):
    """Queried entry is not in the registry."""
