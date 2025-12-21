#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import datetime
import string
import time
import shutil

# ==========================================================
# TRON COLOR THEME (COSMETIC ONLY)
# ==========================================================
RESET   = "\033[0m"
DIM     = "\033[2m"
BOLD    = "\033[1m"

CYAN    = "\033[36m"
CYAN_B  = "\033[96m"
BLUE    = "\033[34m"
WHITE   = "\033[37m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"

SEP = f"{CYAN}{DIM}" + "━" * 56 + RESET

def header(title):
    print()
    print(SEP)
    print(f"{CYAN_B}{BOLD}▣ {title}{RESET}")
    print(SEP)

def section(title):
    print(f"\n{CYAN_B}{BOLD}{title}{RESET}")

def kv(k, v):
    print(f"  {BLUE}{k:<10}{RESET}: {WHITE}{v}{RESET}")

def info(msg):    print(f"{CYAN}{msg}{RESET}")
def warn(msg):    print(f"{YELLOW}{msg}{RESET}")
def error(msg):   print(f"{RED}{msg}{RESET}")
def success(msg): print(f"{GREEN}{msg}{RESET}")

# ==========================================================
# safe execution
# ==========================================================
def run(argv, capture=False, env=None, timeout=None):
    if capture:
        return subprocess.check_output(argv, text=True, env=env, timeout=timeout).strip()
    subprocess.check_call(argv, env=env, timeout=timeout)

def safe(argv):
    try:
        return subprocess.check_output(argv, text=True).strip()
    except Exception:
        return ""

# ==========================================================
# validation helpers
# ==========================================================
def is_printable_no_space(s):
    return s and all(c in string.printable and not c.isspace() for c in s)

def clamp_timeout(val, default="12"):
    try:
        t = int(val)
        return str(min(60, max(1, t)))
    except Exception:
        return default

# ==========================================================
# git helpers
# ==========================================================
def has_commits():
    return bool(safe(["git", "rev-parse", "--verify", "HEAD"]))

def git_config(key):
    return safe(["git", "config", key])

def git_config_set(key, value):
    run(["git", "config", "--local", key, value])

def has_remote(name="origin"):
    remotes = safe(["git", "remote"]).splitlines()
    return name in remotes

def validate_remote_url(url):
    try:
        subprocess.check_call(
            ["git", "ls-remote", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Connection timed out while contacting the remote."
    except subprocess.CalledProcessError:
        return False, "Git could not access this repository URL."

# ==========================================================
# tagging helpers
# ==========================================================
def tag_exists(tag):
    return subprocess.call(
        ["git", "show-ref", "--tags", "--verify", "--quiet", f"refs/tags/{tag}"]
    ) == 0

def next_free_version(major, minor, patch):
    while True:
        candidate = f"v{major}.{minor}.{patch+1}"
        if not tag_exists(candidate):
            return candidate
        patch += 1

# ==========================================================
# commit summary enforcement
# ==========================================================
def enforce_summary_limit(msg, limit=72):
    lines = msg.strip().splitlines()
    if not lines:
        return msg
    s = lines[0]
    if len(s) <= limit:
        return msg
    cut = s[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    lines[0] = cut
    return "\n".join(lines)

# ==========================================================
# identity
# ==========================================================
def read_identity():
    n = git_config("user.name")
    e = git_config("user.email")
    if n or e:
        return n, e, "repo"
    n = safe(["git", "config", "--global", "user.name"])
    e = safe(["git", "config", "--global", "user.email"])
    if n or e:
        return n, e, "global"
    return "", "", "none"

def prompt_identity(n, e):
    info("\nEnter commit identity (blank keeps current):")
    return (
        input(f"{BLUE}Name [{n}]: {RESET}").strip() or n,
        input(f"{BLUE}Email [{e}]: {RESET}").strip() or e,
    )

# ==========================================================
# LLM helpers (unchanged)
# ==========================================================
def has_llm():
    return shutil.which("llm") is not None

def list_llm_models():
    out = safe(["llm", "models"])
    models = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith(":"):
            continue
        core = line.split("(", 1)[0].strip()
        model_id = core.split(":")[-1].strip()
        if is_printable_no_space(model_id):
            models.append({"id": model_id, "label": line})
    return models

# ==========================================================
# MAIN
# ==========================================================
def main():
    if safe(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        error("Not inside a Git repository.")
        sys.exit(1)

    bootstrap = not has_commits()

    last = "v0.0.0" if bootstrap else safe(["git", "describe", "--tags", "--abbrev=0"]) or "v0.0.0"
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", last)
    major, minor, patch = map(int, m.groups()) if m else (0, 0, 0)
    next_version = next_free_version(major, minor, patch)

    name, email, source = read_identity()
    if source == "none":
        name, email = prompt_identity("", "")
        source = "prompted"

    run(["git", "add", "."])
    files = safe(["git", "diff", "--cached", "--name-only"]).splitlines()
    if not files:
        info("Nothing to commit.")
        sys.exit(0)

    commit_msg = enforce_summary_limit(input(f"{BLUE}Commit message: {RESET}").strip())

    header("GITGO :: REVIEW")

    section("IDENTITY")
    kv("Name", name)
    kv("Email", email)

    section("RELEASE")
    kv("Version", next_version)

    section("MESSAGE")
    print(f"\n{WHITE}{commit_msg}{RESET}\n")

    input(f"{BLUE}Press Enter to commit and continue…{RESET}")

    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email
    })

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_msg = f"""{commit_msg}

Version: {next_version}
Timestamp: {ts}
"""

    subprocess.check_call(["git", "commit", "-m", final_msg], env=env)
    subprocess.check_call(["git", "tag", "-a", next_version, "-m", final_msg], env=env)

    # ======================================================
    # REMOTE HANDLING (NEW, ELEGANT, SAFE)
    # ======================================================
    if not has_remote("origin"):
        warn("\nNo git remote named 'origin' is configured.")
        info("A remote is required to push commits and tags.")

        url = input(f"{BLUE}Enter remote repository URL (leave blank to skip push): {RESET}").strip()
        if not url:
            success(f"Local commit and tag created: {next_version}")
            info("Add a remote later using:")
            print(f"{DIM}  git remote add origin <url>{RESET}")
            sys.exit(0)

        ok, reason = validate_remote_url(url)
        if not ok:
            error("\nRemote validation failed.")
            warn(reason)
            info("Fix the URL or repository access, then run gitgo again.")
            sys.exit(1)

        run(["git", "remote", "add", "origin", url])
        success("Remote 'origin' added successfully.")

    branch = safe(["git", "branch", "--show-current"]) or "main"

    try:
        run(["git", "push", "-u", "origin", branch])
        run(["git", "push", "origin", next_version])
    except subprocess.CalledProcessError:
        error("\nPush failed.")
        info("Your commit and tag are safe locally.")
        info("Resolve authentication or permissions, then run:")
        print(f"{DIM}  git push -u origin {branch}{RESET}")
        print(f"{DIM}  git push origin {next_version}{RESET}")
        sys.exit(1)

    success(f"Released {next_version}")

if __name__ == "__main__":
    main()
