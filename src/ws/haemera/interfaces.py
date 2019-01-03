import pyramid.interfaces
import zope.interface


class ISettings(pyramid.interfaces.ISettings):
    """Dictionary of application configuration settings."""


class IDatabase(zope.interface.Interface):
    pass
