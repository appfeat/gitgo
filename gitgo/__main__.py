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

SEP = f"{CYAN}{DIM}" + "━" * 48 + RESET

def header(title):
    print()
    print(SEP)
    print(f"{CYAN_B}{BOLD}▣ {title}{RESET}")
    print(SEP)

def section(title):
    print(f"\n{CYAN_B}{BOLD}{title}{RESET}")

def kv(k, v):
    print(f"  {BLUE}{k:<8}{RESET}: {WHITE}{v}{RESET}")

def info(msg): print(f"{CYAN}{msg}{RESET}")
def warn(msg): print(f"{YELLOW}{msg}{RESET}")
def success(msg): print(f"{GREEN}{msg}{RESET}")
def error(msg): print(f"{RED}{BOLD}ERROR: {msg}{RESET}")

# ==========================================================
# safe execution
# ==========================================================
def run(argv, capture=False, env=None, timeout=None):
    if capture:
        return subprocess.check_output(argv, text=True, env=env, timeout=timeout).strip()
    subprocess.check_call(argv, env=env, timeout=timeout)

def safe(argv):
    try:
        return subprocess.check_output(argv, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return ""

# ==========================================================
# validation & environment
# ==========================================================
def is_printable_no_space(s):
    return s and all(c in string.printable and not c.isspace() for c in s)

def clamp_timeout(val, default="12"):
    try:
        t = int(val)
        return str(min(60, max(1, t)))
    except Exception:
        return default

def check_git_environment():
    """Validates if the directory is a repo and has a valid remote."""
    # 1. Check if inside a work tree
    if safe(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        warn("Current folder is not a Git repository.")
        choice = input(f"{BLUE}Initialize new Git repository here? [y/N]: {RESET}").lower()
        if choice == 'y':
            run(["git", "init"])
            success("Initialized empty Git repository.")
        else:
            info("Exiting cleanly.")
            sys.exit(0)

    # 2. Check for remote
    remote_url = safe(["git", "remote", "get-url", "origin"])
    if not remote_url:
        warn("No remote 'origin' detected.")
        url = input(f"{BLUE}Enter remote URL (or leave blank to skip): {RESET}").strip()
        if url:
            try:
                # Validate remote exists/is reachable
                info(f"Validating remote: {url}...")
                run(["git", "ls-remote", url], capture=True, timeout=10)
                run(["git", "remote", "add", "origin", url])
                success(f"Remote 'origin' added: {url}")
            except Exception as e:
                error(f"Could not validate remote: {url}\nEnsure the URL is correct and you have access.")
                sys.exit(1)
        else:
            warn("Proceeding without a remote. Push will not be possible.")

# ==========================================================
# git helpers
# ==========================================================
def has_commits():
    return bool(safe(["git", "rev-parse", "--verify", "HEAD"]))

def git_config(key):
    return safe(["git", "config", key])

def git_config_set(key, value):
    run(["git", "config", "--local", key, value])

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

def enforce_summary_limit(msg, limit=72):
    lines = msg.strip().splitlines()
    if not lines: return msg
    s = lines[0]
    if len(s) <= limit: return msg
    cut = s[:limit]
    if " " in cut: cut = cut.rsplit(" ", 1)[0]
    lines[0] = cut
    return "\n".join(lines)

def read_identity():
    n = git_config("user.name")
    e = git_config("user.email")
    if n or e: return n, e, "repo"
    n = safe(["git", "config", "--global", "user.name"])
    e = safe(["git", "config", "--global", "user.email"])
    if n or e: return n, e, "global"
    return "", "", "none"

def prompt_identity(n, e):
    info("\nEnter commit identity (blank keeps current):")
    return (
        input(f"{BLUE}Name [{n}]: {RESET}").strip() or n,
        input(f"{BLUE}Email [{e}]: {RESET}").strip() or e,
    )

# ==========================================================
# dashboard
# ==========================================================
def show_repo_dashboard():
    name, email, source = read_identity()
    model = git_config("gitgo.model")
    timeout = git_config("gitgo.timeout")

    header("GITGO :: REPOSITORY STATUS")

    section("LOCATION")
    kv("Path", os.getcwd())
    kv("Branch", safe(["git", "branch", "--show-current"]) or "(detached)")

    section("IDENTITY")
    kv("Name", name or "(not set)")
    kv("Email", email or "(not set)")

    section("REMOTES")
    remotes = safe(["git", "remote", "-v"])
    if remotes:
        for l in remotes.splitlines():
            if "(fetch)" in l: print(f"  {WHITE}{l}{RESET}")
    else:
        kv("Origin", "NOT CONFIGURED")

    section("WORKING TREE")
    status = safe(["git", "status", "--short"])
    kv("Status", "CLEAN" if not status else f"DIRTY ({len(status.splitlines())} files changed)")

    section("RECENT COMMITS")
    log = safe(["git", "log", "-3", "--pretty=format:%h | %ad | %s", "--date=short"])
    if log:
        for l in log.splitlines():
            print(f"  {WHITE}{l}{RESET}")
    else:
        kv("History", "No commits yet")

    print(SEP)
    print(f"{CYAN}1){RESET} Proceed to Commit/Release")
    print(f"{CYAN}Q){RESET} Quit")
    
    choice = input(f"\n{BLUE}Action: {RESET}").strip().lower()
    if choice == 'q':
        sys.exit(0)
    elif choice != '1':
        print("Invalid choice. Exiting.")
        sys.exit(0)

# ==========================================================
# LLM helpers
# ==========================================================
def has_llm():
    return shutil.which("llm") is not None

def list_llm_models():
    out = safe(["llm", "models"])
    models = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith(":"): continue
        core = line.split("(", 1)[0].strip()
        model_id = core.split(":")[-1].strip()
        if is_printable_no_space(model_id):
            models.append({"id": model_id, "label": line})
    return models

def pick_model(models):
    section("AI MODEL SELECTION")
    for i, m in enumerate(models[:2], 1):
        print(f"  {CYAN}{i}){RESET} {WHITE}{m['label']}{RESET}")
    print(f"  {CYAN}3){RESET} More models…")

    c = input(f"{BLUE}Select model [1]: {RESET}").strip()
    if c == "3":
        for i, m in enumerate(models, 1):
            print(f"  {CYAN}{i}){RESET} {WHITE}{m['label']}{RESET}")
        sel = input(f"{BLUE}Select model: {RESET}").strip()
        if not sel or not sel.isdigit(): return models[0]
        return models[int(sel) - 1]
    if c.isdigit() and int(c) in (1, 2): return models[int(c) - 1]
    return models[0]

def wait_with_countdown(proc, timeout):
    remaining = int(timeout)
    while remaining > 0:
        if proc.poll() is not None: return True
        msg = f"{CYAN}AI generating commit message… {remaining}s remaining{RESET}"
        print(f"\r{msg:<80}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    return False

# ==========================================================
# MAIN
# ==========================================================
def main():
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print("gitgo :: Interactive Git release assistant.")
        sys.exit(0)

    # NEW: Environment and Dashboard flow
    check_git_environment()
    show_repo_dashboard()

    # --- ensure local branch is up to date ---
    branch = safe(["git", "branch", "--show-current"])
    upstream = safe(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])

    if branch and upstream:
        run(["git", "fetch", "--quiet"])
        behind = safe(["git", "rev-list", "--count", f"{branch}..{upstream}"])
        if behind.isdigit() and int(behind) > 0:
            warn(f"Local branch is behind {upstream} by {behind} commit(s).")
            c = input(f"{BLUE}Fetch and fast-forward? [y/N]: {RESET}").strip().lower()
            if c == "y":
                try:
                    run(["git", "merge", "--ff-only", upstream])
                    success("Repository updated.")
                except Exception:
                    error("Fast-forward failed. Resolve manually.")
                    sys.exit(1)

    bootstrap = not has_commits()

    if not bootstrap and not safe(["git", "status", "--porcelain"]):
        info("Nothing to commit. Working tree is clean.")
        sys.exit(0)

    # Identity verification
    name, email, source = read_identity()
    if source == "none":
        name, email = prompt_identity("", "")
        source = "prompted"

    # Staging
    run(["git", "add", "."])
    files = safe(["git", "diff", "--cached", "--name-only"]).splitlines()
    if not files:
        info("No staged changes.")
        sys.exit(0)

    # Versioning
    last = "v0.0.0" if bootstrap else safe(["git", "describe", "--tags", "--abbrev=0"]) or "v0.0.0"
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", last)
    major, minor, patch = map(int, m.groups()) if m else (0, 0, 0)
    next_version = next_free_version(major, minor, patch)

    message_mode = git_config("gitgo.message-mode") or "ai"
    commit_msg = None

    # AI vs Manual Logic
    if message_mode == "manual" or not has_llm():
        if not has_llm() and message_mode == "ai":
            warn("AI tools not found. Falling back to manual.")
        msg = input(f"{BLUE}Commit message: {RESET}").strip()
        commit_msg = enforce_summary_limit(msg)
    else:
        # AI Logic (simplified for brevity)
        models = list_llm_models()
        model_id = git_config("gitgo.model")
        timeout = clamp_timeout(git_config("gitgo.timeout"))
        model = next((m for m in models if m["id"] == model_id), models[0])
        
        diff = safe(["git", "diff", "--cached", "--unified=0"])[:15000]
        prompt = f"Summarize these changes into a git commit message:\n{diff}"
        
        p = subprocess.Popen(["llm", "-m", model["id"], prompt], stdout=subprocess.PIPE, text=True)
        if wait_with_countdown(p, timeout):
            out, _ = p.communicate()
            commit_msg = enforce_summary_limit(out.strip())
        else:
            p.kill()
            warn("AI Timed out.")
            commit_msg = enforce_summary_limit(input(f"{BLUE}Manual message: {RESET}").strip())

    # Final Review and Execute
    header("FINAL REVIEW")
    kv("Version", next_version)
    kv("Message", commit_msg)
    
    confirm = input(f"\n{GREEN}Commit and push? [Y/n]: {RESET}").strip().lower()
    if confirm == 'n':
        sys.exit(0)

    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, 
                "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email})

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    final_msg = f"{commit_msg}\n\nVersion: {next_version}\nTimestamp: {ts}"

    run(["git", "commit", "-m", final_msg], env=env)
    run(["git", "tag", "-a", next_version, "-m", final_msg], env=env)

    if safe(["git", "remote"]):
        branch = safe(["git", "branch", "--show-current"]) or "main"
        try:
            run(["git", "push", "-u", "origin", branch])
            run(["git", "push", "origin", next_version])
            success(f"Released {next_version}")
        except Exception as e:
            error(f"Push failed: {e}")
    else:
        success(f"Committed and tagged {next_version} (Local only).")

if __name__ == "__main__":
    main()
