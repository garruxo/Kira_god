# -*- coding: utf-8 -*-
"""
red_kira.py - Abrir conexiones https de forma que funcionen también en Android.

En Android, Python no siempre encuentra los certificados del sistema y las conexiones https fallan con
«CERTIFICATE_VERIFY_FAILED». Si está el paquete 'certifi' (va dentro del APK con Kivy), se usan sus certificados.
Nunca se desactiva la verificación: si no hay certificados válidos, la conexión falla (mejor que conectarse a ciegas).
"""
import ssl
import urllib.request

_CONTEXTO = None


def contexto_ssl():
    global _CONTEXTO
    if _CONTEXTO is None:
        try:
            import certifi
            _CONTEXTO = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            _CONTEXTO = ssl.create_default_context()
    return _CONTEXTO


def abrir(req, timeout=30):
    """Como urllib.request.urlopen, con los certificados correctos para https."""
    url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
    if url.startswith("https://"):
        return urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())
    return urllib.request.urlopen(req, timeout=timeout)
