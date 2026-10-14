"""
Minimal Django settings so h5pxblock.utils can be imported outside the LMS.
"""
import django
from django.conf import settings

if not settings.configured:
    settings.configure()
    django.setup()
