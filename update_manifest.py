"""
update_manifest.py
Script to fetch latest manifest and diff from server,
compatible with 'Update Manifest' workflow.
"""

import asyncio
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

from tqdm import tqdm

from GkmasObjectManager import GkmasManifest, fetch
from GkmasObjectManager.const import WAYBACK_COMMITS_DATABASE_LOCAL
from GkmasObjectManager.utils import _json_dump, _json_load


def fetch_one_manifest(revision: int, commit_hash: str, prog: tqdm) -> GkmasManifest:

    manifest = fetch(this_revision=revision, _hash=commit_hash)
    prog.update(1)
    return manifest


async def fetch_all_manifests(commits: dict[str, str]) -> list[GkmasManifest]:

    with tqdm(total=len(commits), desc="Fetching manifests") as prog:
        return await asyncio.gather(
            *[
                asyncio.to_thread(fetch_one_manifest, int(revision), commit_hash, prog)
                for revision, commit_hash in commits.items()
            ]
        )


def sanitize_canon_repr(canon_repr: dict, revision: int) -> str:
    return "|".join(
        [
            f"{revision:04d}",
            canon_repr["objectName"],
            canon_repr["md5"],
            str(canon_repr["size"]),
            ",".join(map(str, canon_repr.get("dependencies", []))),
        ]
    )


def append_index(index: dict, manifest: GkmasManifest) -> None:

    for obj in manifest.assetbundles:
        ab_id = index["ab_id_lookup"][obj.id]
        index["assetBundleList"][ab_id]["history"].append(
            sanitize_canon_repr(obj.canon_repr, manifest.revision.this)
        )

    for obj in manifest.resources:
        res_id = index["res_id_lookup"][obj.id]
        index["resourceList"][res_id]["history"].append(
            sanitize_canon_repr(obj.canon_repr, manifest.revision.this)
        )


def _rebuild_index():

    commits = _json_load(WAYBACK_COMMITS_DATABASE_LOCAL)
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
        "ab_id_lookup": {
            obj.id: idx for idx, obj in enumerate(manifests[-1].assetbundles)
        },
        "res_id_lookup": {
            obj.id: idx for idx, obj in enumerate(manifests[-1].resources)
        },
        "urlFormat": manifests[-1].urlformat,
    }

    for i in tqdm(range(len(manifests)), desc="Building index"):
        if i == 0:
            append_index(index, manifests[i])
        else:
            append_index(index, manifests[i] - manifests[i - 1])

    del index["ab_id_lookup"]
    del index["res_id_lookup"]
    _json_dump(index, "wayback_index.json")


def fetch_one(path: Path, rev: int, pc: bool):
    fetch(base_revision=rev, pc=pc).export(
        path / f"v{rev:04}.json", force_overwrite=True
    )


async def do_update(path: str, pc: bool = False) -> bool:
    """Check for manifest update from server and optionally update all diff revisions."""

    path = Path(path)
    m_remote = fetch(pc=pc)
    rev_remote = m_remote.revision.canon_repr
    rev_local = int((path / "LATEST_REVISION").read_text())

    if rev_remote == rev_local:
        print("No update available.")
        return False

    # Only write to file after sanity check;
    # this number is used to construct commit message in workflow.
    (path / "LATEST_REVISION").write_text(str(rev_remote))

    m_remote.export(path / "v0000.json", force_overwrite=True)
    await asyncio.gather(
        *[asyncio.to_thread(fetch_one, path, i, pc) for i in range(1, rev_remote)]
    )

    return True


def rebuild_index(rev_hash: str) -> bool:
    """rebuild file history index ("wayback machine")"""

    revision, commit_hash = rev_hash.split("|")

    commits = _json_load(WAYBACK_COMMITS_DATABASE_LOCAL)
    commits[revision] = commit_hash
    commits = dict(sorted(commits.items(), key=lambda x: int(x[0])))
    _json_dump(commits, WAYBACK_COMMITS_DATABASE_LOCAL)

    subprocess.run(["python", "wayback_build_index.py"], check=True)


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument(
        "--rebuild-wayback-index",
        type=str,
        help='rebuild file history index (requires "<revision>|<commit_hash>" from the last manifest update)',
    )
    args = parser.parse_args()

    if args.rebuild_wayback_index:
        sys.exit(not rebuild_index(args.rebuild_wayback_index))

    HAS_UPDATE = asyncio.run(do_update("manifests"))
    HAS_UPDATE_PC = asyncio.run(do_update("manifests_pc", pc=True))
    sys.exit(not (HAS_UPDATE or HAS_UPDATE_PC))  # avoids short-circuiting
