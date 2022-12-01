from tippo import Dict, Mapping, Protocol, TypeVar, Union, runtime_checkable

_ET = TypeVar("_ET")
_VT = TypeVar("_VT")
_ST = TypeVar("_ST")


@runtime_checkable
class RegistryProtocol(Protocol[_ET, _VT]):
    """Protocol for registry-like interfaces."""

    def update(self, updates):
        # type: (_ST, Mapping[_ET, _VT]) -> _ST
        """Update entries."""

    def query(self, entry):
        # type: (_ET) -> _VT
        """
        Query value for entry.

        :raises EntryNotFoundError: Entry not in the registry.
        """

    def get(self, entry, fallback=None):
        # type: (_ET, Union[_VT, None]) -> Union[_VT, None]
        """Get value for entry, return fallback value if not in the registry."""

    def to_dict(self):
        # type: () -> Dict[_ET, _VT]
        """Convert to dictionary."""
