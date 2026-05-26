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

from GkmasObjectManager import fetch
from GkmasObjectManager.const import WAYBACK_COMMITS_DATABASE_LOCAL
from GkmasObjectManager.utils import _json_dump, _json_load


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
