class RegisttroException(Exception):
    """Base registtro exception."""


class EntryNotFoundError(Exception):
    """Queried entry is not in the registry."""
