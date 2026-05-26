"""
manifest/
Manifest (object database) management.
Entry point of the GkmasObjectManager package.
"""

from json import JSONDecodeError
from pathlib import Path
from urllib.parse import urljoin

from google.protobuf.message import DecodeError

from ..const import (
    GKMAS_API_HEADER,
    GKMAS_API_URL,
    GKMAS_API_URL_PC,
    GKMAS_OCTOCACHE_IV,
    GKMAS_OCTOCACHE_KEY,
    GKMAS_ONLINEPDB_KEY,
    GKMAS_ONLINEPDB_KEY_PC,
    WAYBACK_COMMITS_DATABASE_REMOTE,
    WAYBACK_MANIFEST_URL_TEMPLATE,
    PathArgtype,
)
from ..utils import _json_load, _rget
from .decrypt import AESCBCDecryptor
from .manifest import GkmasManifest
from .octodb_pb2 import pdbytes2dict


def fetch(
    this_revision: int = -1,
    base_revision: int = 0,
    _hash: str = "",
    pc: bool = False,
) -> GkmasManifest:
    """
    Requests an online manifest by the specified revision.
    Algorithm courtesy of github.com/DreamGallery/HatsuboshiToolkit

    Args:
        this_revision (int): The revision number of the manifest to fetch.
            Defaults to -1 (latest).
            Older revisions will be fetched from the commit history
            of **this repository**, instead of the game server.
        base_revision (int): The "base" revision number of the manifest.
            Defaults to 0 (standalone latest).
            This API return the *difference* between the specified base
            revision and the latest.
        pc (bool): Whether to use the PC manifest API.
            Defaults to False (mobile).
    """
    #   _hash (str): The commit hash of the manifest to fetch.
    #       Defaults to "" (ignored).
    #       If specified, overrides commit hash lookup by 'this_revision',
    #       but still requires 'this_revision' to be specified for sanity check.
    #       Exclusively used in rebuilding wayback index before remote database is updated.
    #       NOT FOR GENERAL USE.

    if this_revision != -1:

        if _hash:
            commit_hash = _hash
        else:
            commits = _json_load(WAYBACK_COMMITS_DATABASE_REMOTE)
            if str(this_revision) not in commits:
                raise ValueError(
                    f"Manifest revision {this_revision} not found in history."
                )
            commit_hash = commits[str(this_revision)]

        url = WAYBACK_MANIFEST_URL_TEMPLATE.format(
            hash=commit_hash,
            revision=base_revision,
        )
        manifest = GkmasManifest(_rget(url).json(), base_revision)
        assert manifest.revision.canon_repr == int(
            this_revision
        ), "Manifest revision mismatch with commit history record."
        return manifest

    url = urljoin(GKMAS_API_URL_PC if pc else GKMAS_API_URL, str(base_revision))
    req = _rget(url, headers=GKMAS_API_HEADER)

    enc = req.content
    dec = AESCBCDecryptor(
        GKMAS_ONLINEPDB_KEY_PC if pc else GKMAS_ONLINEPDB_KEY, enc[:16]
    ).process(enc[16:])
    return GkmasManifest(pdbytes2dict(dec), base_revision)


def load(src: PathArgtype, base_revision: int = 0) -> GkmasManifest:
    """
    Initializes a manifest from the given offline source.
    The protobuf referred to can be either encrypted or not.
    Also supports importing from JSON.

    Args:
        src (Union[str, Path]): Path to the manifest file.
            Can be the path to
            - an encrypted octocache (usually named 'octocacheevai'),
            - a decrypted protobuf, or
            - a JSON file exported from another manifest.
        base_revision (int) = 0: The revision number of the base manifest.
            **Must be manually specified if loading a diff genereated
            by GkmasObjectManager older than or equal to v0.4-beta.**
    """

    try:
        return GkmasManifest(_json_load(src), base_revision)

    except JSONDecodeError:
        enc = Path(src).read_bytes()
        try:
            return GkmasManifest(pdbytes2dict(enc), base_revision)
        except DecodeError:
            dec = AESCBCDecryptor(GKMAS_OCTOCACHE_KEY, GKMAS_OCTOCACHE_IV).process(enc)
            return GkmasManifest(pdbytes2dict(dec[16:]), base_revision)  # trim md5 hash
