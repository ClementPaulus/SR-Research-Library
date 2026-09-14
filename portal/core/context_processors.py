"""Template context shared by every page."""

from django.conf import settings


def portal(request):
    return {
        "PORTAL_PUBLIC_BASE_URL": settings.PORTAL_PUBLIC_BASE_URL,
        "PORTAL_SUPPORT_CONTACT": settings.PORTAL_SUPPORT_CONTACT,
        "PORTAL_DEVELOPMENT_EMAIL_CAPTURE": getattr(settings, "PORTAL_DEVELOPMENT_EMAIL_CAPTURE", False),
        "ADMISSION_BOUNDARY": ("Library admission confirms that the record meets the organizational requirements. "
                               "It does not certify the scientific claims."),
    }
