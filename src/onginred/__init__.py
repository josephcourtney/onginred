from importlib.metadata import version

from .sockets import SockFamily, SockProtocol, SockType

__all__ = ["SockFamily", "SockProtocol", "SockType", "__version__"]

__version__ = version("onginred")
