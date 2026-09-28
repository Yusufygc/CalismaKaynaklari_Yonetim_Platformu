class PKMBaseError(Exception):
    """Tum proje hatalari icin temel sinif."""


class ValidationError(PKMBaseError):
    """Girdi kurallara uymadigi zaman."""


class ResourceNotFoundError(PKMBaseError):
    """ID'ye sahip kayit bulunamadiginda."""


class InvalidURLError(ValidationError):
    """URL formati bozuk oldugunda."""


class DuplicateRecordError(PKMBaseError):
    """Ayni isimde kayit eklenmek isteniginde."""
