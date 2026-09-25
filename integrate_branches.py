"""integrate_branches.py -- fold the unmerged GitHub branches into main.

Run from the repo root:

    python integrate_branches.py            # build and check locally; push nothing
    python integrate_branches.py --push     # same, then push the result to origin/main

WHAT IT DOES
    1. Refuses to start on a dirty working tree or a half-finished merge.
    2. Fetches origin and checks that every branch in the plan below still
       matches what was reviewed on 2026-09-25: it exists, it still carries the
       reviewed tip commit (so nothing new slipped in unreviewed), and each
       branch marked "skip" or "already merged" still is.
    3. Builds a local branch `integrate/<date>` from origin/main and merges the
       planned branches into it in order, each as its own merge commit, so any
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

    00_STATE/MANIFEST.csv is the one exception. The 2026-09-14 reconciliation
    rewrote the whole file, and main has changed it since; a union would give
    duplicate rows for one path with different hashes. Main's copy is kept and
    the re-audit is listed as a follow-up.

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
import subprocess
import sys
from pathlib import Path

SCRIPT_VERSION = "1.0"
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
    ("claude/player-valuation-walkthrough-uiyl8b", "e668929",
     "Aging-curve walkthrough workbook (20_CODE/valuation_walkthrough.py) and the "
     "2026-09-25 session; one commit on top of main."),
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
KEEP_MAIN = {"00_STATE/MANIFEST.csv"}


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------
def git(*args: str, check: bool = True) -> str:
    """Run git and return stdout. Errors carry git's own message."""
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def ok(*args: str) -> bool:
    return subprocess.run(["git", *args], capture_output=True).returncode == 0


def ref(branch: str) -> str:
    return f"{REMOTE}/{branch}"


def is_ancestor(a: str, b: str) -> bool:
    return ok("merge-base", "--is-ancestor", a, b)


# ---------------------------------------------------------------------------
# 1-2. preconditions and the plan check
# ---------------------------------------------------------------------------
def preflight() -> None:
    root = Path(git("rev-parse", "--show-toplevel"))
    if Path.cwd().resolve() != root.resolve():
        raise SystemExit(f"run from the repo root: {root}")
    if git("status", "--porcelain"):
        raise SystemExit("working tree has uncommitted changes; commit or stash them first")
    gitdir = Path(git("rev-parse", "--absolute-git-dir"))
    for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD"):
        if (gitdir / marker).exists():
            raise SystemExit(f"a git operation is in progress ({marker}); finish or abort it first")


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
        if f in KEEP_MAIN:
            git("checkout", "--ours", "--", f)
            followups.append(f"{f}: kept main's copy; re-audit it against `git ls-files` "
                             f"(the {branch} reconciliation was not carried over)")
        elif UNION_OK.match(f):
            text = Path(f).read_text(encoding="utf-8")
            try:
                new = HUNK.sub(union_hunk, text)
            except ValueError as e:
                raise SystemExit(f"{f}: cannot auto-resolve ({e}). The merge of {branch} is "
                                 f"left in progress for a person to finish.")
            if "<<<<<<<" in new or ">>>>>>>" in new:
                raise SystemExit(f"{f}: conflict markers not in diff3 form; resolve by hand")
            Path(f).write_text(new, encoding="utf-8")
        else:
            raise SystemExit(f"{f}: conflict outside the state files; the merge of {branch} "
                             f"is left in progress for a person to finish.")
        git("add", "--", f)


# ---------------------------------------------------------------------------
# 3-5. build and check
# ---------------------------------------------------------------------------
def build(merge: list) -> tuple[str, list[str]]:
    work = f"integrate/{dt.date.today().isoformat()}"
    git("checkout", "-q", "-B", work, ref(BASE))
    followups: list[str] = []
    for name, _, why in merge:
        print(f"\nmerging {name}\n  {why}")
        r = subprocess.run(
            ["git", "-c", "merge.conflictstyle=diff3", "merge", "--no-ff", "--no-edit",
             "-m", f"Merge {name} into {BASE}", ref(name)],
            capture_output=True, text=True)
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
    return work, followups


def verify(work: str, merge: list) -> None:
    base = ref(BASE)
    # Conflict markers anywhere in a changed text file.
    changed = git("diff", "--name-only", base, work).splitlines()
    for f in changed:
        p = Path(f)
        if p.suffix in {".md", ".py", ".csv", ".txt", ".html", ".json"} and p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|) ", text, re.M):
                raise SystemExit(f"conflict marker left in {f}")
    # Every changed Python file still compiles.
    bad = []
    for f in changed:
        if f.endswith(".py") and Path(f).exists():
            r = subprocess.run([sys.executable, "-m", "py_compile", f], capture_output=True, text=True)
            if r.returncode:
                bad.append(f"{f}: {r.stderr.strip()}")
    if bad:
        raise SystemExit("files that no longer compile:\n  " + "\n  ".join(bad))
    # Each planned branch is contained; main is contained (fast-forward possible).
    for name, _, _ in merge:
        assert is_ancestor(ref(name), work), f"{name} missing from the result"
    assert is_ancestor(base, work), "result does not contain main; push would not fast-forward"
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

    preflight()
    start = git("rev-parse", "--abbrev-ref", "HEAD")
    check_plan(merge)
    work, followups = build(merge)
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
    git("checkout", "-q", start)
    print(f"back on {start}; the result stays on local branch {work}")


if __name__ == "__main__":
    main()
