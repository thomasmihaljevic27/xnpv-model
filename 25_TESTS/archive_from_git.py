"""archive_from_git.py -- write files from a git commit into 90_ARCHIVE/<date>/.

WHY THIS EXISTS
    90_ARCHIVE/ is gitignored, so it exists only on the machine that fills it.
    When a file is retired in a commit made elsewhere (the cloud session),
    pulling that commit deletes the laptop's copy and puts nothing in
    90_ARCHIVE/. This script restores the archive copy from git history: it
    reads each file AS IT WAS in the given commit and writes the exact bytes
    to 90_ARCHIVE/<date>/<original path>. Bytes are written as git stores
    them, so there is no PowerShell re-encoding (the `git show ... > file`
    route writes UTF-16 on Windows PowerShell 5.1, which Python cannot read).

    It can run before or after the pull: the files are read from history, not
    from the working folder. It never deletes or overwrites anything; a file
    already in the archive folder is skipped and reported.

HOW TO RUN (Windows PowerShell, from the repo root):
    python 25_TESTS\\archive_from_git.py <commit> <date> <path> [<path> ...]
    e.g. python 25_TESTS\\archive_from_git.py 02f6fda 2026-10-02 20_CODE/ep_age_scraper.py
A path may be a folder: every file under it in that commit is archived.
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_VERSION = "1.0"
ROOT = Path(__file__).resolve().parents[1]


def _git(*args) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True).stdout


def files_in(commit: str, path: str) -> list:
    """Every tracked file at `path` (a file or a folder) in `commit`."""
    out = _git("ls-tree", "-r", "--name-only", commit, "--", path).decode("utf-8")
    return [p for p in out.splitlines() if p]


def archive(commit: str, date: str, paths) -> int:
    dest_root = ROOT / "90_ARCHIVE" / date
    written = 0
    for path in paths:
        found = files_in(commit, path)
        if not found:
            print(f"  NOT IN {commit}: {path}")
            continue
        for p in found:
            dest = dest_root / p
            if dest.exists():
                print(f"  already archived, skipped: {dest.relative_to(ROOT)}")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_git("show", f"{commit}:{p}"))
            written += 1
    print(f"  {written} file(s) written under {dest_root.relative_to(ROOT)}")
    return written


def main(argv=sys.argv[1:]):
    print(f"archive_from_git.py v{SCRIPT_VERSION}")
    if len(argv) < 3:
        raise SystemExit(__doc__)
    commit, date, paths = argv[0], argv[1], argv[2:]
    _git("rev-parse", "--verify", f"{commit}^{{commit}}")      # stops on an unknown commit
    archive(commit, date, paths)


if __name__ == "__main__":
    main()
