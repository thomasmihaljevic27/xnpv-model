"""integrate_branches.py -- fold the unmerged GitHub branches into main.

Run from the repo root:

    python integrate_branches.py            # build and check locally; push nothing
    python integrate_branches.py --push     # same, then push the result to origin/main

    It works from any branch and does not need a clean working tree: the merge
    is built in a separate, temporary git worktree, so the folder you run it
    from (its branch, its edits, its untracked files) is never touched.

WHAT CHANGED IN v1.1 (first run on the Windows laptop, 2026-09-25)
    v1.0 merged inside the folder it was run from and so refused any
    untracked file. On the laptop that was the script's own untracked copy,
    which the rebuild branch's merge would then have collided with. v1.1
    builds in its own worktree instead. It also keeps each file's line
    endings (a Windows checkout may be CRLF; Python's default text mode
    would have rewritten every resolved state file) and reads git's output as
    UTF-8 rather than the Windows code page.

WHAT CHANGED IN v1.2 (2026-09-25, after the laptop sync)
    The laptop's sync script stages everything, and before the .gitignore fix
    reached that branch it committed `.env.bak_20260925` (the placeholder
    template, no keys) and a copy of this script onto the walkthrough branch
    (f10a67e). That moved the branch past its reviewed tip, which is why the
    push was refused. v1.2 pins the new tip, and adds a last step: any tracked
    file that the merged .gitignore excludes is taken out of the index (kept
    on disk), so a stray backup or archive file cannot reach main.

WHAT IT DOES
    1. Fetches origin and checks that every branch in the plan below still
       matches what was reviewed on 2026-09-25: it exists, it still carries the
       reviewed tip commit (so nothing new slipped in unreviewed), and each
       branch marked "skip" or "already merged" still is.
    3. Builds a local branch `integrate/<date>` from origin/main, in a
       temporary worktree, and merges the planned branches into it in order, each as its own merge commit, so any
       one of them can be reverted later with `git revert -m 1 <merge>`.
    4. Resolves conflicts only where a mechanical rule is safe (below) and
       stops, leaving the merge for a person, anywhere else.
    5. Checks the result: no conflict markers left, every changed Python file
       compiles, every planned branch is an ancestor of the result.
    6. With --push only: pushes the result to origin/main, and only as a
       fast-forward. Without --push it prints the command instead.

THE CONFLICT RULE, AND WHY IT IS SAFE
    Every conflict found in the 2026-09-25 trial sits in the running state and
    log files (00_STATE/*.md, 00_STATE/sessions/*.md, CLAUDE.md). Parallel
    sessions each APPENDED an entry at the same spot: a change-log entry, a
    session log, a standing flag, a new rule. For those the right answer is to
    keep both. The script checks that this is really what happened before it
    acts: it asks git for the common ancestor's text of each conflict
    (diff3 style) and keeps both sides ONLY if every ancestor line survives
    unchanged on the incoming branch's side, meaning the branch purely added
    text. Anything else (the branch rewrote or deleted a line main also
    touched) is not auto-resolved.

    00_STATE/MANIFEST.csv is one exception. The 2026-09-14 reconciliation
    rewrote the whole file, and main has changed it since; a union would give
    duplicate rows for one path with different hashes. Main's copy is kept and
    the re-audit is listed as a follow-up. integrate_branches.py is the other:
    the version already merged (the rebuild branch's, current) is kept.

    Any other conflicted file stops the run.

WHAT IS DELIBERATELY LEFT OUT (see SKIP below for each reason)
    - claude/wizardly-goodall-25okn3: the pre-migration repository, an unrelated
      history. Merging it would revert about 4,000 lines of later code. Its one
      unique contribution, three CLAUDE.md rules, was ported by hand into
      claude/amazing-johnson-cllbgl on 2026-09-25.
    - claude/nifty-euler-u5c5vm: enables an unpinned third-party plugin for
      every future session. Opt in with --include-typesafe.

Requires only git and Python 3.9+. Touches no file in 10_SOURCE or 30_OUTPUT.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_VERSION = "1.2"
REMOTE = "origin"
BASE = "main"

# ---------------------------------------------------------------------------
# THE PLAN, as reviewed 2026-09-25. Order matters: the largest branch goes
# first so each later one merges onto the combined state it will live in.
# `tip` pins the commit that was reviewed; if a branch has moved since, the
# run stops rather than merging work nobody has looked at.
# ---------------------------------------------------------------------------
MERGE = [
    ("claude/amazing-johnson-cllbgl", None,
     "The player-model rebuild: all 50_REBUILD code, reviews, the corrected "
     "scorecard and the decision brief. Already carries main's latest two commits."),
    ("claude/player-valuation-walkthrough-uiyl8b", "f10a67e",
     "Aging-curve walkthrough workbook (20_CODE/valuation_walkthrough.py) and the "
     "2026-09-25 session, plus the laptop sync commit (a copy of this script and an "
     ".env backup, which the untrack step below removes)."),
    ("claude/awesome-curie-9o6hh1", "8e53125",
     "Two-page plain-language project overview (.docx and .pdf) in Thomas's edited "
     "version, with its CLAUDE.md rule."),
    ("claude/elite-aging-curve-weighting-klbvbz", "1cd08f5",
     "2026-09-14 elite-player aging audit: two read-only diagnostics and the "
     "session record. Scripts never run on real ages; the record says so."),
    ("claude/cap-adjusted-contract-surplus-gi9wxu", "36af817",
     "2026-09-14 cap-inflation session: the g/rho standing flag, "
     "04_Discount_Heterogeneity_Sequence.md, the restored .docx extension, and "
     "90_ARCHIVE untracked to match .gitignore."),
]

# The rebuild branch is still being worked on, so its tip is not pinned; it is
# checked to contain main instead (it must, or its merge would conflict).
UNPINNED_MUST_CONTAIN_BASE = {"claude/amazing-johnson-cllbgl"}

OPTIONAL = {
    "--include-typesafe": ("claude/nifty-euler-u5c5vm", "dc4dc97",
                           "Adds .claude/settings.json enabling the TypeSafe plugin."),
}

SKIP = {
    "claude/wizardly-goodall-25okn3":
        "unrelated pre-migration history; merging would revert later code. Its three "
        "CLAUDE.md rules were ported into the rebuild branch.",
    "claude/nifty-euler-u5c5vm":
        "unpinned third-party plugin (tracks upstream's default branch), never loaded "
        "or verified; it would be enabled in every session. Opt in with --include-typesafe.",
}

# Contained in main already; listed so the run confirms it and says so.
ALREADY_MERGED = ["50_rebuild", "claude/affectionate-galileo-mh9f7w",
                  "claude/relaxed-clarke-onaulu"]
# Contained in the rebuild branch, so merged by it.
MERGED_VIA_REBUILD = ["claude/loving-maxwell-rd3w5v"]

# Files where "keep both sides" is allowed, provided the branch only added text.
UNION_OK = re.compile(r"^(00_STATE/[^/]+\.md|00_STATE/sessions/[^/]+\.md|CLAUDE\.md)$")
# Files where the side already merged ("ours": main plus the branches merged so
# far) wins, with the reason printed as a follow-up.
KEEP_OURS = {
    "00_STATE/MANIFEST.csv":
        "kept main's copy; re-audit it against `git ls-files` (the 2026-09-14 "
        "reconciliation on the branch was not carried over)",
    # The laptop sync committed a copy of an older version of this script onto
    # the walkthrough branch; the rebuild branch, merged first, carries the
    # current one.
    "integrate_branches.py":
        "kept the rebuild branch's (current) version of this script",
}


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------
# Where git runs. The plan check runs in the folder the script was started
# from; everything that changes files runs in the temporary worktree (set in
# main()), so the user's own folder is only ever read.
CWD: Path | None = None


def run(args: list[str]) -> subprocess.CompletedProcess:
    """git's output is UTF-8 (commit messages here carry non-ASCII text); on
    Windows Python would otherwise decode it with the ANSI code page and fail."""
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=CWD)


def git(*args: str, check: bool = True) -> str:
    """Run git and return stdout. Errors carry git's own message."""
    r = run(["git", *args])
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def ok(*args: str) -> bool:
    return run(["git", *args]).returncode == 0


def read_text(p: Path) -> tuple[str, str]:
    """A file's text with LF line ends, and the line end it had on disk.

    newline="" stops Python translating anything, so a CRLF checkout (usual on
    Windows) is seen as it is. The conflict patterns are written for LF, so the
    text is normalised for matching and written back in its own convention."""
    with open(p, encoding="utf-8", newline="") as fh:
        raw = fh.read()
    eol = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), eol


def write_text(p: Path, text: str, eol: str) -> None:
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", eol) if eol != "\n" else text)


def ref(branch: str) -> str:
    return f"{REMOTE}/{branch}"


def is_ancestor(a: str, b: str) -> bool:
    return ok("merge-base", "--is-ancestor", a, b)


# ---------------------------------------------------------------------------
# 1-2. preconditions and the plan check
# ---------------------------------------------------------------------------
def preflight() -> Path:
    """Only checks that this is the repository. Uncommitted or untracked files
    in the current folder do not matter: nothing is built here."""
    if not ok("rev-parse", "--show-toplevel"):
        raise SystemExit("not inside the xNPV git repository; cd into it first")
    return Path(git("rev-parse", "--show-toplevel"))


def check_plan(merge: list) -> None:
    print(f"fetching {REMOTE} ...")
    git("fetch", "--prune", REMOTE)
    base = ref(BASE)
    print(f"\n{'branch':<46}{'ahead':>6}{'behind':>7}  status")
    for name, tip, _ in merge:
        r = ref(name)
        if not ok("rev-parse", "--verify", "-q", r):
            raise SystemExit(f"{name}: not on {REMOTE}")
        # PINNED TIP: the branch must still end at the reviewed commit.
        if tip and not git("rev-parse", r).startswith(tip):
            raise SystemExit(f"{name}: tip moved from reviewed {tip} to "
                             f"{git('rev-parse', '--short', r)}; review the new commits first")
        if name in UNPINNED_MUST_CONTAIN_BASE and not is_ancestor(base, r):
            raise SystemExit(f"{name}: does not contain {BASE}; merge {BASE} into it first")
        ahead = git("rev-list", "--count", f"{base}..{r}")
        behind = git("rev-list", "--count", f"{r}..{base}")
        print(f"{name:<46}{ahead:>6}{behind:>7}  merge")
    for name in ALREADY_MERGED:
        if ok("rev-parse", "--verify", "-q", ref(name)):
            state = "already in main" if is_ancestor(ref(name), base) else "NOT IN MAIN: review"
            print(f"{name:<46}{'':>13}  {state}")
    rebuild = ref(MERGE[0][0])
    for name in MERGED_VIA_REBUILD:
        if ok("rev-parse", "--verify", "-q", ref(name)):
            state = "merged via the rebuild branch" if is_ancestor(ref(name), rebuild) else "NOT CONTAINED: review"
            print(f"{name:<46}{'':>13}  {state}")
    for name, why in SKIP.items():
        if any(name == m[0] for m in merge):
            continue
        print(f"{name:<46}{'':>13}  skip: {why}")
    # Any branch on the remote that the plan does not mention is reported, so a
    # new one is not silently ignored.
    known = ({m[0] for m in merge} | set(SKIP) | set(ALREADY_MERGED)
             | set(MERGED_VIA_REBUILD) | {o[0] for o in OPTIONAL.values()} | {BASE})
    remote = [b.strip().removeprefix(f"{REMOTE}/")
              for b in git("branch", "-r", "--format=%(refname:short)").splitlines()]
    unknown = [b for b in remote if b not in known and b != "HEAD" and b != REMOTE]
    if unknown:
        print("\nNOT IN THE PLAN (left alone; review before the next run):")
        for b in unknown:
            print(f"  {b}")


# ---------------------------------------------------------------------------
# 4. conflict resolution
# ---------------------------------------------------------------------------
HUNK = re.compile(
    r"<<<<<<< [^\n]*\n(?P<ours>.*?)"
    r"\|\|\|\|\|\|\| [^\n]*\n(?P<base>.*?)"
    r"=======\n(?P<theirs>.*?)"
    r">>>>>>> [^\n]*\n", re.S)


def union_hunk(m: re.Match) -> str:
    """Keep both sides of one conflict, if the incoming branch only ADDED text.

    `base` is the common ancestor's text at the conflict. When every ancestor
    line is still present on the incoming side, that side's change was pure
    insertion, and main's side (which carries its own version of those lines)
    plus the inserted lines loses nothing. Otherwise refuse."""
    ours, base, theirs = m["ours"], m["base"], m["theirs"]
    base_lines = base.splitlines()
    theirs_lines = theirs.splitlines()
    if any(line not in theirs_lines for line in base_lines):
        raise ValueError("incoming side rewrote or removed ancestor text")
    # The branch's additions: its lines minus the ancestor lines it kept.
    added, pool = [], list(base_lines)
    for line in theirs_lines:
        if line in pool:
            pool.remove(line)
        else:
            added.append(line)
    added_text = "\n".join(added).strip("\n")
    if not added_text:
        return ours
    sep = "" if ours.endswith("\n\n") or not ours else "\n"
    return ours + sep + added_text + "\n\n"


def resolve(conflicted: list[str], branch: str, followups: list[str]) -> None:
    for f in conflicted:
        if f in KEEP_OURS:
            git("checkout", "--ours", "--", f)
            followups.append(f"{f} (from {branch}): {KEEP_OURS[f]}")
        elif UNION_OK.match(f):
            text, eol = read_text(CWD / f)
            try:
                new = HUNK.sub(union_hunk, text)
            except ValueError as e:
                raise SystemExit(f"{f}: cannot auto-resolve ({e}). The merge of {branch} is "
                                 f"left in progress for a person to finish.")
            if "<<<<<<<" in new or ">>>>>>>" in new:
                raise SystemExit(f"{f}: conflict markers not in diff3 form; resolve by hand")
            write_text(CWD / f, new, eol)
        else:
            raise SystemExit(f"{f}: conflict outside the state files; the merge of {branch} "
                             f"is left in progress for a person to finish.")
        git("add", "--", f)


# ---------------------------------------------------------------------------
# 3-5. build and check
# ---------------------------------------------------------------------------
def build(merge: list, work: str) -> list[str]:
    followups: list[str] = []
    for name, _, why in merge:
        print(f"\nmerging {name}\n  {why}")
        r = run(["git", "-c", "merge.conflictstyle=diff3", "merge", "--no-ff", "--no-edit",
                 "-m", f"Merge {name} into {BASE}", ref(name)])
        if r.returncode != 0:
            conflicted = git("diff", "--name-only", "--diff-filter=U").splitlines()
            if not conflicted:
                raise SystemExit(f"merge of {name} failed:\n{r.stderr or r.stdout}")
            print(f"  conflicts: {', '.join(conflicted)}")
            resolve(conflicted, name, followups)
            git("commit", "--no-edit", "-q")
            print("  resolved (additions kept from both sides)")
        else:
            print("  clean")
    return followups


def untrack_ignored(followups: list[str]) -> None:
    """Take out of the index every tracked file the merged .gitignore excludes.

    `git ls-files -ci --exclude-standard` lists files that are tracked AND
    match an ignore rule: things committed before the rule existed, or staged
    by a blanket `git add -A`. The files stay on disk; only git stops tracking
    them. Listed one by one so nothing leaves silently."""
    stray = [f for f in git("ls-files", "-ci", "--exclude-standard").splitlines() if f]
    if not stray:
        print("\nno tracked files match .gitignore")
        return
    print("\nuntracking files the merged .gitignore excludes:")
    for f in stray:
        print(f"  {f}")
    git("rm", "-q", "--cached", "--", *stray)
    git("commit", "-q", "-m", "Untrack files the merged .gitignore excludes\n\n"
        + "\n".join(f"- {f}" for f in stray))
    followups.append(f"untracked {len(stray)} ignored file(s): {', '.join(stray)} "
                     "(removed from main going forward; still in the source branch's history)")


def verify(work: str, merge: list) -> None:
    base = ref(BASE)
    # Conflict markers anywhere in a changed text file.
    changed = git("diff", "--name-only", base, work).splitlines()
    for f in changed:
        p = CWD / f
        if p.suffix in {".md", ".py", ".csv", ".txt", ".html", ".json"} and p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|) ", text, re.M):
                raise SystemExit(f"conflict marker left in {f}")
    # Every changed Python file still compiles.
    bad = []
    for f in changed:
        if f.endswith(".py") and (CWD / f).exists():
            # compile() rather than py_compile: nothing is written (no __pycache__).
            try:
                compile((CWD / f).read_bytes(), f, "exec")
            except SyntaxError as e:
                bad.append(f"{f}: {e}")
    if bad:
        raise SystemExit("files that no longer compile:\n  " + "\n  ".join(bad))
    # Each planned branch is contained; main is contained (fast-forward possible).
    for name, _, _ in merge:
        assert is_ancestor(ref(name), work), f"{name} missing from the result"
    assert is_ancestor(base, work), "result does not contain main; push would not fast-forward"
    left = git("ls-files", "-ci", "--exclude-standard")
    assert not left, f"tracked files still match .gitignore: {left}"
    # Nothing from the gitignored trees was brought in.
    for tree in ("30_OUTPUT/", "90_ARCHIVE/"):
        added = [f for f in git("diff", "--name-only", "--diff-filter=A", base, work).splitlines()
                 if f.startswith(tree)]
        assert not added, f"merge adds files under {tree}: {added}"
    print(f"\nchecks passed: {len(changed)} files changed against {BASE}; no conflict markers; "
          f"{sum(f.endswith('.py') for f in changed)} Python files compile; "
          f"each planned branch contained; fast-forward to {BASE} possible")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--push", action="store_true",
                    help=f"push the result to {REMOTE}/{BASE} (fast-forward only)")
    for flag, (name, _, why) in OPTIONAL.items():
        ap.add_argument(flag, action="store_true", help=f"also merge {name}: {why}")
    args = ap.parse_args()
    print(f"integrate_branches.py v{SCRIPT_VERSION}")

    merge = list(MERGE)
    for flag, entry in OPTIONAL.items():
        if getattr(args, flag.lstrip("-").replace("-", "_")):
            merge.append(entry)
            SKIP.pop(entry[0], None)

    global CWD
    repo = preflight()
    CWD = repo
    check_plan(merge)

    # THE TEMPORARY WORKTREE. A second checkout of the same repository in a
    # temp folder, on its own branch, sharing the object store and refs. The
    # merge happens there; the folder the script was run from is not touched.
    work = f"integrate/{dt.date.today().isoformat()}"
    git("worktree", "prune")
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line == f"branch refs/heads/{work}":
            raise SystemExit(f"branch {work} is checked out in another worktree; "
                             f"remove it with `git worktree list` / `git worktree remove`")
    tmp = Path(tempfile.mkdtemp(prefix="xnpv_integrate_"))
    wt = tmp / "wt"
    git("worktree", "add", "-q", "-B", work, str(wt), ref(BASE))
    print(f"\nbuilding in a temporary worktree: {wt}")
    try:
        CWD = wt
        followups = build(merge, work)
        untrack_ignored(followups)
        verify(work, merge)

        print("\nmerge commits on", work)
        print(git("log", "--oneline", "--first-parent", f"{ref(BASE)}..{work}"))
        if followups:
            print("\nFOLLOW-UPS:")
            for f in followups:
                print(f"  - {f}")

        if args.push:
            git("push", REMOTE, f"{work}:{BASE}")        # fast-forward only: no --force
            print(f"\npushed {work} to {REMOTE}/{BASE}")
        else:
            print(f"\nNothing pushed. To publish:  git push {REMOTE} {work}:{BASE}")
    except BaseException:
        # Any stop (a refused conflict, a failed check, Ctrl+C): leave the worktree in place so a stopped merge can be finished by hand.
        print(f"\nSTOPPED. The partial merge is in {wt} (branch {work}). Finish it there, "
              f"or discard it with:  git worktree remove --force \"{wt}\"")
        raise
    CWD = repo
    git("worktree", "remove", "--force", str(wt))
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"temporary worktree removed; the result stays on local branch {work}. "
          f"Your own folder and branch were not changed.")


if __name__ == "__main__":
    main()
