from importlib.metadata import version

from onginred.sockets import SockFamily, SockProtocol, SockType

__all__ = ["SockFamily", "SockProtocol", "SockType", "__version__"]

__version__ = version("onginred")
