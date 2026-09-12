<#
.SYNOPSIS
    Two-way GitHub sync for the xNPV model repo.

.DESCRIPTION
    Commits every local change, pulls anything on GitHub that isn't local, and
    pushes the result. Written to be run from either machine (desktop or
    laptop) without editing it: the repo location is taken from the script's
    own folder, not from a hardcoded user path, because the two machines have
    different Windows usernames (Thomas vs thoma).

    Do not run this by double-clicking. Use Sync-Desktop.cmd or Sync-Laptop.cmd,
    which set the execution policy for this one process and keep the window open
    so you can read the output.

.PARAMETER Message
    Commit message. Defaults to the machine name plus a timestamp, so the
    history says which machine a given sync came from.

.PARAMETER RepoPath
    Override the repo location. Only needed if this script is run from outside
    the repo folder.

.EXAMPLE
    .\sync.ps1
    .\sync.ps1 -Message "rebuilt draft yield curve"
#>

param(
    [string]$Message  = "",
    [string]$RepoPath = ""
)

# Deliberately NOT setting $ErrorActionPreference = 'Stop'. Git writes routine
# progress information to stderr (branch names, push destinations, "Everything
# up-to-date"), and under 'Stop' PowerShell treats that as a terminating error
# and kills the script on a successful command. Exit codes are checked by hand
# instead, via $LASTEXITCODE after each git call.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step { param([string]$Text) Write-Host "`n$Text" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host $Text -ForegroundColor Green }
function Write-Warn { param([string]$Text) Write-Host $Text -ForegroundColor Yellow }
function Write-Bad  { param([string]$Text) Write-Host $Text -ForegroundColor Red }

# Runs a git command and streams its output to the console as plain text.
# The 2>&1 merge is what stops PowerShell from painting git's normal stderr
# chatter red and making a clean run look like a failure.
function Invoke-Git {
    param([string[]]$GitArgs)
    & git @GitArgs 2>&1 | ForEach-Object { Write-Host "  $_" }
    return $LASTEXITCODE
}

# ---------------------------------------------------------------------------
# 0. Locate the repo and confirm the tools exist
# ---------------------------------------------------------------------------

# $PSScriptRoot is the folder this .ps1 lives in. Since the script is committed
# to the repo root, that folder IS the repo on whichever machine is running it.
# This is the whole reason one script serves both machines.
if ([string]::IsNullOrWhiteSpace($RepoPath)) { $RepoPath = $PSScriptRoot }

if (-not (Test-Path $RepoPath)) {
    Write-Bad "Repo path not found: $RepoPath"
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Bad "git is not on PATH. Install Git for Windows, then reopen PowerShell."
    exit 1
}

Push-Location $RepoPath

try {
    Write-Host "xNPV sync" -ForegroundColor White
    Write-Host "  machine : $env:COMPUTERNAME ($env:USERNAME)"
    Write-Host "  repo    : $RepoPath"

    # rev-parse fails outside a git working tree. Catching it here gives a clear
    # message instead of a wall of git errors from the commands further down.
    # --absolute-git-dir (not --git-dir) because --git-dir returns a path that
    # is sometimes relative and sometimes absolute depending on where it is run
    # from, and Join-Path silently produces nonsense when handed an absolute
    # second argument. The absolute form removes the ambiguity.
    $gitDir = (git rev-parse --absolute-git-dir 2>$null)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitDir)) {
        Write-Bad "Not a git repository: $RepoPath"
        exit 1
    }
    $gitDir = $gitDir.Trim()

    # -----------------------------------------------------------------------
    # 1. GUARD: refuse to run during an unfinished rebase, merge or cherry-pick
    # -----------------------------------------------------------------------
    # This is the state that stranded the desktop in detached HEAD. When git is
    # mid-operation, add/commit/pull compound the mess rather than fixing it, so
    # the script stops and prints the two commands that resolve it.
    $inProgress = @(
        (Join-Path $gitDir 'rebase-merge'),
        (Join-Path $gitDir 'rebase-apply'),
        (Join-Path $gitDir 'MERGE_HEAD'),
        (Join-Path $gitDir 'CHERRY_PICK_HEAD')
    ) | Where-Object { Test-Path $_ }

    if ($inProgress) {
        Write-Bad "`nGit is mid-operation. Nothing was changed."
        Write-Host "  Finish it:  git rebase --continue   (or: git merge --continue)"
        Write-Host "  Or undo it: git rebase --abort      (or: git merge --abort)"
        Write-Host "  'abort' rewinds to before the operation started. No commits are lost."
        Write-Host ""
        git status
        exit 1
    }

    # -----------------------------------------------------------------------
    # 2. GUARD: refuse to run on a detached HEAD
    # -----------------------------------------------------------------------
    # rev-parse --abbrev-ref returns the literal string "HEAD" when you are not
    # on a branch. Pushing from that state needs a different syntax and pulling
    # is impossible, so bail out rather than produce confusing errors.
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($branch -eq 'HEAD') {
        Write-Bad "`nDetached HEAD - not on a branch. Nothing was changed."
        Write-Host "  Reattach with: git checkout main"
        exit 1
    }
    Write-Host "  branch  : $branch"

    # -----------------------------------------------------------------------
    # 3. Show what is about to be committed
    # -----------------------------------------------------------------------
    # --short lists modified/added/deleted paths. .gitignore already excludes
    # 30_OUTPUT/, 90_ARCHIVE/, .env, 10_SOURCE/* (bar the four approved vendor
    # CSVs) and anything matching *CONFIDENTIAL*, so nothing confidential or
    # regenerable can appear in this list.
    Write-Step "Local changes"
    $dirty = git status --short
    if ($dirty) { $dirty | ForEach-Object { Write-Host "  $_" } }
    else        { Write-Host "  (none)" -ForegroundColor DarkGray }

    # -----------------------------------------------------------------------
    # 4. Stage and commit
    # -----------------------------------------------------------------------
    # -A stages new files, edits AND deletions. A plain 'git add .' misses
    # deletions on older git versions, which silently leaves removed files in
    # the repo.
    if ($dirty) {
        if ((Invoke-Git @('add', '-A')) -ne 0) {
            Write-Bad "git add failed. Stopping before the commit."
            exit 1
        }

        if ([string]::IsNullOrWhiteSpace($Message)) {
            $Message = "Sync from $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        }

        # --cached --quiet exits non-zero when the staging area has content.
        # Without this check a no-op run would leave a failure exit code behind
        # and look like something went wrong.
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) {
            Write-Step "Committing"
            if ((Invoke-Git @('commit', '-m', $Message)) -ne 0) {
                Write-Bad "Commit failed. Stopping before the pull."
                exit 1
            }
        }
    }

    # -----------------------------------------------------------------------
    # 5. Pull down anything on GitHub that is not local
    # -----------------------------------------------------------------------
    # --no-rebase forces a merge pull. Rebase rewrites local commits on top of
    # the remote's and parks you in detached HEAD when it stalls partway, which
    # is exactly what happened on the desktop. A merge pull leaves you on your
    # branch whatever happens; the cost is an occasional merge commit, which is
    # nothing on a single-author repo.
    #
    # Note this does NOT restore gitignored files: 30_OUTPUT/ comes back by
    # re-running the pipeline, not by pulling. And a file deleted on the other
    # machine will be deleted here. That is the intended behaviour of a sync.
    Write-Step "Pulling from GitHub"
    if ((Invoke-Git @('pull', '--no-rebase', 'origin', $branch)) -ne 0) {
        Write-Bad "`nPull failed or hit a conflict. Nothing has been pushed."
        Write-Host "  If it is a conflict: edit the marked files, then run"
        Write-Host "    git add -A; git commit; git push"
        Write-Host "  To back out entirely: git merge --abort"
        Write-Host ""
        git status --short
        exit 1
    }

    # -----------------------------------------------------------------------
    # 6. Push, retrying on transient network failure
    # -----------------------------------------------------------------------
    # A laptop on flaky wifi fails a push for reasons that have nothing to do
    # with the repo. Three attempts with widening gaps covers a dropped
    # connection without masking a real rejection, which fails identically all
    # three times and still reports.
    Write-Step "Pushing to GitHub"
    $pushed = $false
    foreach ($delay in @(0, 3, 8)) {
        if ($delay -gt 0) {
            Write-Warn "  Push failed, retrying in $delay seconds..."
            Start-Sleep -Seconds $delay
        }
        if ((Invoke-Git @('push', '-u', 'origin', $branch)) -eq 0) { $pushed = $true; break }
    }

    if (-not $pushed) {
        Write-Bad "`nPush failed after 3 attempts."
        Write-Host "  Check your connection, then rerun. Your commits are safe locally."
        exit 1
    }

    # -----------------------------------------------------------------------
    # 7. Report
    # -----------------------------------------------------------------------
    Write-Step "Done"
    Write-Ok "  Branch '$branch' is in sync with GitHub."
    Write-Host "  Latest commits:"
    git log --oneline -3 | ForEach-Object { Write-Host "    $_" }
    exit 0
}
finally {
    # Always return to the caller's directory, including on an early exit.
    Pop-Location
}
