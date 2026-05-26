import asyncio
import json

from tqdm import tqdm

from GkmasObjectManager import GkmasManifest
from GkmasObjectManager.const import (
    WAYBACK_COMMITS_DATABASE,
    WAYBACK_IGNORED_FIELDS,
    WAYBACK_MANIFEST_URL_TEMPLATE,
)
from GkmasObjectManager.utils import _rget


def fetch_one(version: str, hash: str, prog: tqdm) -> GkmasManifest:

    r = _rget(WAYBACK_MANIFEST_URL_TEMPLATE.format(hash=hash, revision=int(version)))
    manifest = GkmasManifest(r.json())
    assert manifest.revision.canon_repr == int(version)

    prog.update(1)
    return manifest


async def fetch_all(commits: dict[str, str]) -> list[GkmasManifest]:

    with tqdm(total=len(commits), desc="Fetching manifests") as prog:
        return await asyncio.gather(
            *[
                asyncio.to_thread(fetch_one, version, hash, prog)
                for version, hash in commits.items()
            ]
        )


def sanitize_canon_repr(canon_repr: dict, revision: int) -> dict:

    ret = {"revision": revision}

    for key in canon_repr:
        if key not in WAYBACK_IGNORED_FIELDS:
            ret[key] = canon_repr[key]

    return ret


def append_index(index: dict, manifest: GkmasManifest) -> None:

    for obj in manifest.assetbundles:
        index["assetBundleList"][obj.id]["history"].append(
            sanitize_canon_repr(obj.canon_repr, manifest.revision.this)
        )

    for obj in manifest.resources:
        index["resourceList"][obj.id]["history"].append(
            sanitize_canon_repr(obj.canon_repr, manifest.revision.this)
        )


def main():

    with open(WAYBACK_COMMITS_DATABASE) as fin:
        commits = json.load(fin)

    manifests = asyncio.run(fetch_all(commits))

    index = {
        "latest_revision": manifests[-1].revision.canon_repr,
        "assetBundleList": [
            {"id": obj.id, "name": obj.name, "history": []}
            for obj in manifests[-1].assetbundles
        ],
        "resourceList": [
            {"id": obj.id, "name": obj.name, "history": []}
            for obj in manifests[-1].resources
        ],
        "urlFormat": manifests[-1].urlformat,
    }

    for i in tqdm(range(len(manifests)), desc="Building index"):
        if i == 0:
            append_index(index, manifests[i])
        else:
            append_index(index, manifests[i] - manifests[i - 1])

    with open("wayback_index.json", "w") as fout:
        json.dump(index, fout, indent=4)


if __name__ == "__main__":
    main()
