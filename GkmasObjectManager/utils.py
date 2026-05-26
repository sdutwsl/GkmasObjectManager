"""
utils.py
General-purpose utilities: hashing, decorators, etc.
"""

import requests
from cryptography.hazmat.primitives import hashes

from .const import REQUEST_TIMEOUT


def _rget(url: str, **kwargs) -> requests.Response:
    """A wrapper around requests.get() with timeout and sanity check."""
    r = requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
    r.raise_for_status()
    return r


def sha256sum(data: bytes) -> bytes:
    """Calculates SHA-256 hash of the given data."""
    digest = hashes.Hash(hashes.SHA256())
    digest.update(data)
    return digest.finalize()


def md5sum(data: bytes) -> bytes:
    """Calculates MD5 hash of the given data."""
    digest = hashes.Hash(hashes.MD5())
    digest.update(data)
    return digest.finalize()
