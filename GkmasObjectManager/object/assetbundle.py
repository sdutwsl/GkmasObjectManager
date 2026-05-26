"""
assetbundle.py
Unity asset bundle downloading, deobfuscation, and media extraction.
"""

from .resource import GkmasResource


class GkmasAssetBundle(GkmasResource):
    """
    An assetbundle. Class inherits from GkmasResource.

    Attributes:
        All attributes from GkmasResource, plus
        name (str): Human-readable name, appended with '.unity3d'.
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
        self.name += ".unity3d"
        self._idname = f"AB[{self.id:05}] '{self.name}'"

    def __repr__(self) -> str:
        return f"<GkmasAssetBundle {self._idname}>"

    @property
    def canon_repr(self) -> dict:
        canon = super().canon_repr
        canon["name"] = canon["name"].removesuffix(".unity3d")
        return canon
