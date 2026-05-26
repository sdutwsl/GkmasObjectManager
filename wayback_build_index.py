import asyncio

from tqdm import tqdm

from GkmasObjectManager import GkmasManifest, fetch
from GkmasObjectManager.const import WAYBACK_COMMITS_DATABASE, WAYBACK_IGNORED_FIELDS
from GkmasObjectManager.utils import _json_dump, _json_load


def fetch_one_manifest(revision: int, prog: tqdm) -> GkmasManifest:

    manifest = fetch(revision)
    prog.update(1)
    return manifest


async def fetch_all_manifests(commits: dict[str, str]) -> list[GkmasManifest]:

    with tqdm(total=len(commits), desc="Fetching manifests") as prog:
        return await asyncio.gather(
            *[
                asyncio.to_thread(fetch_one_manifest, int(revision), prog)
                for revision in list(commits.keys())[-3:]
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

    commits = _json_load(WAYBACK_COMMITS_DATABASE)
    manifests = asyncio.run(fetch_all_manifests(commits))

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

    _json_dump(index, "wayback_index.json")


if __name__ == "__main__":
    main()
