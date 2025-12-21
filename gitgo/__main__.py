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
# TRON COLOR THEME
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
    print(f"\n{SEP}\n{CYAN_B}{BOLD}▣ {title}{RESET}\n{SEP}")

def section(title):
    print(f"\n{CYAN_B}{BOLD}{title}{RESET}")

def kv(k, v):
    print(f"  {BLUE}{k:<8}{RESET}: {WHITE}{v}{RESET}")

def info(msg): print(f"{CYAN}{msg}{RESET}")
def warn(msg): print(f"{YELLOW}{msg}{RESET}")
def success(msg): print(f"{GREEN}{msg}{RESET}")
def error(msg): print(f"{RED}{BOLD}ERROR: {msg}{RESET}")

# ==========================================================
# SYSTEM HELPERS
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

def is_printable_no_space(s):
    return s and all(c in string.printable and not c.isspace() for c in s)

def clamp_timeout(val, default="12"):
    try:
        t = int(val)
        return str(min(60, max(1, t)))
    except Exception:
        return default

# ==========================================================
# GIT CONFIG & IDENTITY
# ==========================================================
def git_config(key):
    return safe(["git", "config", key])

def git_config_set(key, value):
    run(["git", "config", "--local", key, value])

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
    new_n = input(f"{BLUE}Name [{n}]: {RESET}").strip() or n
    new_e = input(f"{BLUE}Email [{e}]: {RESET}").strip() or e
    return new_n, new_e

# ==========================================================
# AI HELPERS
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
        return models[int(sel) - 1] if sel.isdigit() and int(sel) <= len(models) else models[0]
    return models[int(c)-1] if c.isdigit() and int(c) in (1, 2) else models[0]

def wait_with_countdown(proc, timeout):
    remaining = int(timeout)
    while remaining > 0:
        if proc.poll() is not None: return True
        print(f"\r{CYAN}AI generating… {remaining}s remaining{RESET}{' '*20}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    return False

def generate_ai_message(model_id, timeout):
    diff = safe(["git", "diff", "--cached", "--unified=0"])[:15000]
    prompt = f"Improve this Git commit message. Rules: FIRST line ≤ 72 chars. No invented details.\n\nDiff:\n{diff}"
    try:
        p = subprocess.Popen(["llm", "-m", model_id, prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if wait_with_countdown(p, timeout):
            out, err = p.communicate()
            if out.strip(): return enforce_summary_limit(out.strip()), None
            return None, err.strip() or "Empty output"
        p.kill()
        return None, "Timeout"
    except Exception as e:
        return None, str(e)

# ==========================================================
# VERSIONING
# ==========================================================
def tag_exists(tag):
    return subprocess.call(["git", "show-ref", "--tags", "--verify", "--quiet", f"refs/tags/{tag}"]) == 0

def next_free_version(major, minor, patch):
    while True:
        candidate = f"v{major}.{minor}.{patch+1}"
        if not tag_exists(candidate): return candidate
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

# ==========================================================
# CORE WORKFLOW
# ==========================================================
def check_env():
    if safe(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
        warn("Not a Git repository.")
        if input(f"{BLUE}Initialize? [y/N]: {RESET}").lower() == 'y':
            run(["git", "init"])
        else: sys.exit(0)
    
    if not safe(["git", "remote"]):
        warn("No remote origin.")
        url = input(f"{BLUE}Remote URL (blank to skip): {RESET}").strip()
        if url:
            try:
                run(["git", "ls-remote", url], capture=True, timeout=10)
                run(["git", "remote", add, "origin", url])
            except Exception:
                error("Invalid remote. Exiting."); sys.exit(1)

def main():
    check_env()
    
    # Dashboard info
    name, email, source = read_identity()
    model_id = git_config("gitgo.model")
    timeout = clamp_timeout(git_config("gitgo.timeout"))

    header("GITGO :: STATUS")
    kv("Identity", f"{name} <{email}> ({source})")
    kv("Model", model_id or "default")
    kv("Branch", safe(["git", "branch", "--show-current"]))
    
    section("REMOTE")
    print(f"  {safe(['git', 'remote', '-v'])}")

    section("HISTORY")
    print(f"  {safe(['git', 'log', '-2', '--oneline'])}")

    if input(f"\n{BLUE}Proceed to commit? [Y/n]: {RESET}").lower() == 'n': sys.exit(0)

    # Prepare changes
    run(["git", "add", "."])
    if not safe(["git", "status", "--porcelain"]):
        success("Nothing to commit."); sys.exit(0)

    # Resolve Version
    last = safe(["git", "describe", "--tags", "--abbrev=0"]) or "v0.0.0"
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", last)
    major, minor, patch = map(int, m.groups()) if m else (0, 0, 0)
    next_version = next_free_version(major, minor, patch)

    # Initial Message Generation
    message_mode = git_config("gitgo.message-mode") or "ai"
    commit_msg = "No message generated."
    
    if message_mode == "ai" and has_llm():
        models = list_llm_models()
        active_model = next((m for m in models if m["id"] == model_id), models[0])
        commit_msg, err = generate_ai_message(active_model["id"], timeout)
        if err:
            warn(f"\nAI Error: {err}")
            commit_msg = input(f"{BLUE}Manual message: {RESET}").strip()
            git_config_set("gitgo.message-mode", "manual")
    else:
        commit_msg = input(f"{BLUE}Commit message: {RESET}").strip()

    # REVIEW LOOP
    while True:
        header("GITGO :: REVIEW")
        kv("Identity", f"{name} <{email}>")
        kv("Version", next_version)
        section("MESSAGE")
        print(f"{WHITE}{commit_msg}{RESET}")

        print(f"\n{CYAN}1){RESET} Commit & Push  {CYAN}2){RESET} Edit Identity  {CYAN}3){RESET} Edit Message")
        print(f"{CYAN}4){RESET} Change AI/Model  {CYAN}5){RESET} Change Version   {CYAN}6){RESET} Cancel")
        
        c = input(f"\n{BLUE}Choice [1]: {RESET}").strip() or "1"

        if c == "1": break
        elif c == "2":
            name, email = prompt_identity(name, email)
            git_config_set("user.name", name); git_config_set("user.email", email)
            source = "repo"
        elif c == "3":
            commit_msg = enforce_summary_limit(input(f"{BLUE}New message: {RESET}").strip())
        elif c == "4":
            if not has_llm(): continue
            models = list_llm_models()
            chosen = pick_model(models)
            git_config_set("gitgo.model", chosen["id"])
            model_id = chosen["id"]
            timeout = clamp_timeout(input(f"{BLUE}Timeout [{timeout}]: {RESET}") or timeout)
            git_config_set("gitgo.timeout", timeout)
            commit_msg, _ = generate_ai_message(model_id, timeout)
            git_config_set("gitgo.message-mode", "ai")
        elif c == "5":
            next_version = input(f"{BLUE}Version [{next_version}]: {RESET}").strip() or next_version
        elif c == "6": sys.exit(0)

    # Final Execution
    env = os.environ.copy()
    env.update({"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email})
    
    final_body = f"{commit_msg}\n\nVersion: {next_version}\nTimestamp: {datetime.datetime.now()}"
    run(["git", "commit", "-m", final_body], env=env)
    run(["git", "tag", "-a", next_version, "-m", final_body], env=env)
    
    if safe(["git", "remote"]):
        branch = safe(["git", "branch", "--show-current"]) or "main"
        run(["git", "push", "-u", "origin", branch])
        run(["git", "push", "origin", next_version])
        success(f"Released {next_version}")

if __name__ == "__main__":
    main()
