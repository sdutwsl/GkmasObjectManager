"""
update_manifest.py
Script to fetch latest manifest and diff from server,
compatible with 'Update Manifest' workflow.
"""

import sys
from pathlib import Path

import GkmasObjectManager as gom


def do_update(path: str, pc: bool = False) -> bool:
    """Check for manifest update from server and optionally update all diff revisions."""

    path = Path(path)
    m_remote = gom.fetch(pc=pc)
    rev_remote = m_remote.revision.canon_repr
    rev_local = int((path / "LATEST_REVISION").read_text())

    if rev_remote == rev_local:
        print("No update available.")
        return False

    # Only write to file after sanity check;
    # this number is used to construct commit message in workflow.
    (path / "LATEST_REVISION").write_text(str(rev_remote))

    m_remote.export(path / "v0000.json", force_overwrite=True)
    for i in range(1, rev_remote):
        gom.fetch(i, pc=pc).export(path / f"v{i:04}.json", force_overwrite=True)

    return True


if __name__ == "__main__":
    HAS_UPDATE = do_update("manifests")
    HAS_UPDATE_PC = do_update("manifests_pc", pc=True)
    sys.exit(not (HAS_UPDATE or HAS_UPDATE_PC))  # avoids short-circuiting
