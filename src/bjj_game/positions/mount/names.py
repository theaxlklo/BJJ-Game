from ...domain.names import NameResolver, normalize_name
from .catalog import MOUNT_CATALOG

RESOLVER = NameResolver(MOUNT_CATALOG)

__all__ = ["NameResolver", "RESOLVER", "normalize_name"]
