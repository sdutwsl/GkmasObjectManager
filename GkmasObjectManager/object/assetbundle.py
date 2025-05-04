"""
assetbundle.py
Unity asset bundle downloading, deobfuscation, and media extraction.
"""

from pathlib import Path

from ..const import UNITY_SIGNATURE, PathArgtype
from ..media import GkmasDummyMedia
from ..media.audio import GkmasUnityAudio
from ..media.image import GkmasUnityImage
from ..utils import Logger
from .deobfuscate import GkmasAssetBundleDeobfuscator
from .resource import GkmasResource

logger = Logger()


class GkmasAssetBundle(GkmasResource):
    """
    An assetbundle. Class inherits from GkmasResource.

    Attributes:
        All attributes from GkmasResource, plus
        name (str): Human-readable name.
            Appended with '.unity3d' only at download and CSV export.
        crc (int): CRC checksum, unused for now (since scheme is unknown).

    Methods:
        download(
            path: Union[str, Path] = DEFAULT_DOWNLOAD_PATH,
            categorize: bool = True,
            **kwargs,
        ) -> None:
            Downloads and deobfuscates the assetbundle to the specified path.
            Also performs media conversion if applicable.
    """

    def __init__(self, info: dict, url_template: str):
        """
        Initializes an assetbundle with the given information.
        Usually called from GkmasManifest.

        Args:
            info (dict): An info dictionary, extracted from protobuf.
            url_template (str): URL template for downloading the assetbundle.
                {o} will be replaced with self.objectName.
        """

        super().__init__(info, url_template)
        self._idname = f"AB[{self.id:05}] '{self.name}'"

    def __repr__(self):
        return f"<GkmasAssetBundle {self._idname}>"

    def _get_media(self):
        """
        [INTERNAL] Instantiates a high-level media class based on the assetbundle name.
        Used to dispatch download and extraction.
        """

        if self._media is None:
            data = self._download_bytes()
            if self.name.startswith("img_"):
                media_class = GkmasUnityImage
            elif self.name.startswith("sud_"):
                media_class = GkmasUnityAudio
            else:
                media_class = GkmasDummyMedia
            self._media = media_class(self._idname, data, self._mtime)

        return self._media

    def _download_path(self, path: PathArgtype, categorize: bool) -> Path:
        """
        [INTERNAL] Refines the download path based on user input.
        Inherited from GkmasResource, but imposes a '.unity3d' suffix.
        """
        return super()._download_path(path, categorize).with_suffix(".unity3d")

    def _download_bytes(self) -> bytes:
        """
        [INTERNAL] Downloads, and optionally deobfuscates, the assetbundle as raw bytes.
        Sanity checks are implemented in parent class GkmasResource.
        """

        data = super()._download_bytes()

        if not data.startswith(UNITY_SIGNATURE):
            data = GkmasAssetBundleDeobfuscator(self.name).process(data)
            if not data.startswith(UNITY_SIGNATURE):
                logger.warning(f"{self._idname} downloaded but LEFT OBFUSCATED")
                # Unexpected things may happen...
                # So unlike _download_bytes(), here we don't raise an error and abort.

        return data
