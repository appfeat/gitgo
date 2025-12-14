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
# validation
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
# summary enforcement
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
# dashboard (cosmetic)
# ==========================================================
def show_repo_dashboard():
    name, email, source = read_identity()
    model = git_config("gup.model")
    timeout = git_config("gup.timeout")

    header("GUP :: REPOSITORY STATUS")

    section("IDENTITY")
    kv("Name", name or "(not set)")
    kv("Email", email or "(not set)")
    kv("Source", source)

    section("AI CONFIG")
    kv("Model", model or "(not set)")
    kv("Timeout", f"{timeout}s" if timeout else "(default)")

    section("REPO")
    kv("Branch", safe(["git", "branch", "--show-current"]) or "(detached)")
    tag = safe(["git", "describe", "--tags", "--abbrev=0"])
    if tag:
        kv("Tag", tag)

    section("REMOTES")
    remotes = safe(["git", "remote", "-v"])
    if remotes:
        for l in remotes.splitlines():
            print(f"  {WHITE}{l}{RESET}")
    else:
        kv("None", "-")

    section("WORKING TREE")
    kv("Status", "CLEAN" if not safe(["git", "status", "--short"]) else "DIRTY")

    section("RECENT COMMITS")
    log = safe(["git", "log", "-3", "--pretty=format:%h | %ad | %s", "--date=short"])
    if log:
        for l in log.splitlines():
            print(f"  {WHITE}{l}{RESET}")
    else:
        kv("None", "-")

    print(SEP)

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
        if not line or line.endswith(":"):
            continue
        core = line.split("(", 1)[0].strip()
        model_id = core.split(":")[-1].strip()
        if is_printable_no_space(model_id):
            models.append({"id": model_id, "label": line})
    return models

def pick_model(models):
    section("AI MODEL SELECTION")
    for i, m in enumerate(models[:2], 1):
        print(f"  {CYAN}{i}){RESET} {WHITE}{m['label']}{RESET}")
    print(f"  {CYAN}3){RESET} {WHITE}More models…{RESET}")

    c = input(f"{BLUE}Select model [1]: {RESET}").strip()
    if c == "3":
        for i, m in enumerate(models, 1):
            print(f"  {CYAN}{i}){RESET} {WHITE}{m['label']}{RESET}")
        sel = input(f"{BLUE}Select model: {RESET}").strip()
        if not sel or not sel.isdigit():
            return models[0]
        return models[int(sel) - 1]
    if c.isdigit() and int(c) in (1, 2):
        return models[int(c) - 1]
    return models[0]

# ==========================================================
# countdown helper
# ==========================================================
def wait_with_countdown(proc, timeout):
    remaining = int(timeout)
    while remaining > 0:
        if proc.poll() is not None:
            return True
        msg = f"{CYAN}AI generating commit message… {remaining}s remaining{RESET}"
        print(f"\r{msg:<80}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    return False

# ==========================================================
# MAIN
# ==========================================================
def main():
    if safe(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        warn("Not inside a Git repository.")
        sys.exit(1)

    # --- ensure local branch is up to date ---
    branch = safe(["git", "branch", "--show-current"])
    upstream = safe(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])

    if branch and upstream:
        run(["git", "fetch", "--quiet"])
        behind = safe(["git", "rev-list", "--count", f"{branch}..{upstream}"])
        if behind.isdigit() and int(behind) > 0:
            warn(f"Local branch is behind {upstream} by {behind} commit(s).")
            c = input(f"{BLUE}Fetch and fast-forward before continuing? [y/N]: {RESET}").strip().lower()
            if c == "y":
                try:
                    run(["git", "merge", "--ff-only", upstream])
                    success("Repository updated from remote.")
                except Exception:
                    warn("Fast-forward failed. Resolve manually and re-run gup.")
                    sys.exit(1)
            else:
                warn("Aborted due to out-of-date branch.")
                sys.exit(1)

    bootstrap = not has_commits()

    if not bootstrap and not safe(["git", "status", "--porcelain"]):
        info("Nothing to commit.")
        show_repo_dashboard()
        sys.exit(0)

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
        info("No staged changes.")
        show_repo_dashboard()
        sys.exit(0)

    message_mode = git_config("gup.message-mode") or "ai"
    commit_msg = None

    # ---------- MANUAL MODE ----------
    if message_mode == "manual":
        info("Manual commit message mode (press 'a' to switch to AI).")
        msg = input(f"{BLUE}Commit message: {RESET}").strip()
        if msg.lower() != "a":
            commit_msg = enforce_summary_limit(msg)
            git_config_set("gup.message-mode", "manual")
        else:
            message_mode = "ai"

    # ---------- AI MODE ----------
    if message_mode == "ai":
        if not has_llm():
            warn("AI commit messages require the 'llm' tool.")
            warn("Install with: pip install llm")
            warn("Then configure at least one model.")
            commit_msg = enforce_summary_limit(input(f"{BLUE}Commit message: {RESET}").strip())
            git_config_set("gup.message-mode", "manual")
        else:
            models = list_llm_models()
            if not models:
                warn("No LLM models available.")
                warn("Configure models using the 'llm' tool.")
                commit_msg = enforce_summary_limit(input(f"{BLUE}Commit message: {RESET}").strip())
                git_config_set("gup.message-mode", "manual")
            else:
                model_id = git_config("gup.model")
                timeout = clamp_timeout(git_config("gup.timeout"))
                model = next((m for m in models if m["id"] == model_id), models[0])

                def generate_message():
                    diff = safe(["git", "diff", "--cached", "--unified=0"])[:15000]
                    prompt = f"""Improve this Git commit message.

Rules:
- FIRST line ≤ 72 characters.
- Do NOT invent details.

Diff:
{diff}
"""
                    try:
                        p = subprocess.Popen(
                            ["llm", "-m", model["id"], prompt],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        completed = wait_with_countdown(p, timeout)
                        print("\r" + " " * 80 + "\r", end="", flush=True)
                        if not completed:
                            p.kill()
                            return None, "AI request timed out"
                        out, err = p.communicate()
                        if out.strip():
                            return enforce_summary_limit(out.strip()), None
                        return None, err.strip() or "AI returned empty output"
                    except Exception as e:
                        return None, str(e)

                commit_msg, ai_warning = generate_message()

                if ai_warning:
                    warn(f"\n⚠ AI failed: {ai_warning}")
                    print(f"{CYAN}1){RESET} Manual message")
                    print(f"{CYAN}2){RESET} Select another model")
                    print(f"{CYAN}3){RESET} Cancel")
                    c = input(f"{BLUE}Choice: {RESET}").strip()

                    if c == "1":
                        commit_msg = enforce_summary_limit(input(f"{BLUE}Commit message: {RESET}").strip())
                        git_config_set("gup.message-mode", "manual")
                    elif c == "2":
                        model = pick_model(models)
                        git_config_set("gup.model", model["id"])
                        commit_msg, ai_warning = generate_message()
                        if ai_warning:
                            warn(f"AI failed again: {ai_warning}")
                            commit_msg = enforce_summary_limit(input(f"{BLUE}Commit message: {RESET}").strip())
                            git_config_set("gup.message-mode", "manual")
                        else:
                            git_config_set("gup.message-mode", "ai")
                    else:
                        sys.exit(0)
                else:
                    git_config_set("gup.message-mode", "ai")

    # ---------- REVIEW LOOP ----------
    while True:
        header("GUP :: REVIEW")

        section("IDENTITY")
        kv("Name", name)
        kv("Email", email)
        kv("Source", source)

        section("RELEASE")
        kv("Version", next_version)

        section("MESSAGE")
        print(f"\n{WHITE}{commit_msg}{RESET}\n")

        print(f"{CYAN}1){RESET} Commit & push")
        print(f"{CYAN}2){RESET} Edit identity")
        print(f"{CYAN}3){RESET} Edit message")
        print(f"{CYAN}4){RESET} Change AI model & regenerate")
        print(f"{CYAN}5){RESET} Change version")
        print(f"{CYAN}6){RESET} Cancel")

        c = input(f"{BLUE}Choice: {RESET}").strip()

        if c == "1":
            break
        if c == "2":
            name, email = prompt_identity(name, email)
            git_config_set("user.name", name)
            git_config_set("user.email", email)
            source = "repo"
        if c == "3":
            info("Enter commit message (Ctrl+D):")
            commit_msg = enforce_summary_limit(sys.stdin.read().strip())
        if c == "4":
            if not has_llm():
                warn("AI tools not available. Install with: pip install llm")
                continue

            models = list_llm_models()
            if not models:
                warn("No AI models available. Configure using the llm CLI.")
                continue

            model = pick_model(models)
            git_config_set("gup.model", model["id"])

            timeout = clamp_timeout(
                input(f"{BLUE}Timeout seconds (1–60) [{timeout}]: {RESET}") or timeout
            )
            git_config_set("gup.timeout", timeout)

            commit_msg, ai_warning = generate_message()
            if ai_warning:
                warn(f"\n⚠ AI regeneration failed: {ai_warning}\n")
                info("Keeping previous commit message.")
            else:
                git_config_set("gup.message-mode", "ai")
            continue
        if c == "5":
            info("Enter version (format: vMAJOR.MINOR.PATCH)")
            v = input(f"{BLUE}Version [{next_version}]: {RESET}").strip()
            if not v:
                continue
            if not re.match(r"^v\d+\.\d+\.\d+$", v):
                warn("Invalid version format. Use vMAJOR.MINOR.PATCH (e.g. v1.2.3)")
                continue
            if tag_exists(v):
                warn(f"Tag {v} already exists.")
                continue
            next_version = v
            success(f"Version set to {next_version}")
            continue
        if c == "6":
            sys.exit(0)

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
    subprocess.check_call(
        ["git", "tag", "-a", next_version, "-m", final_msg],
        env=env
    )


    branch = safe(["git", "branch", "--show-current"]) or "main"
    run(["git", "push", "-u", "origin", branch])
    run(["git", "push", "origin", next_version])

    success(f"Released {next_version}")

if __name__ == "__main__":
    main()
