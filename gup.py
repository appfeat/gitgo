#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import datetime
import string

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

def info(msg):
    print(f"{CYAN}{msg}{RESET}")

def warn(msg):
    print(f"{YELLOW}{msg}{RESET}")

def success(msg):
    print(f"{GREEN}{msg}{RESET}")

# ==========================================================
# safe execution (UNCHANGED)
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
# validation (UNCHANGED)
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
# git helpers (UNCHANGED)
# ==========================================================
def has_commits():
    return bool(safe(["git", "rev-parse", "--verify", "HEAD"]))

def git_config(key):
    return safe(["git", "config", key])

def git_config_set(key, value):
    run(["git", "config", key, value])

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
# summary enforcement (UNCHANGED)
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
# identity (UNCHANGED LOGIC)
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
# dashboard (COSMETIC ONLY)
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
    branch = safe(["git", "branch", "--show-current"]) or "(detached)"
    kv("Branch", branch)

    tag = safe(["git", "describe", "--tags", "--abbrev=0"])
    if tag:
        kv("Tag", tag)

    section("REMOTES")
    remotes = safe(["git", "remote", "-v"])
    if remotes:
        for line in remotes.splitlines():
            print(f"  {WHITE}{line}{RESET}")
    else:
        kv("None", "-")

    section("WORKING TREE")
    clean = not safe(["git", "status", "--short"])
    kv("Status", "CLEAN" if clean else "DIRTY")

    section("RECENT COMMITS")
    commits = safe(
        ["git", "log", "-3", "--pretty=format:%h | %ad | %s", "--date=short"]
    )
    if commits:
        for line in commits.splitlines():
            print(f"  {WHITE}{line}{RESET}")
    else:
        kv("None", "-")

    print(SEP)

# ==========================================================
# models (UNCHANGED LOGIC, COSMETIC OUTPUT)
# ==========================================================
def list_llm_models():
    out = safe(["llm", "models"])
    models = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith(":"):
            continue
        label = line
        core = line.split("(", 1)[0].strip()
        model_id = core.split(":")[-1].strip()
        if is_printable_no_space(model_id):
            models.append({"id": model_id, "label": label})
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
        return models[int(sel) - 1]
    if c.isdigit() and int(c) in (1, 2):
        return models[int(c) - 1]
    return models[0]

# ==========================================================
# repo check (UNCHANGED)
# ==========================================================
if safe(["git", "rev-parse", "--is-inside-work-tree"]) != "true":
    warn("Not inside a Git repository.")
    sys.exit(1)

bootstrap = not has_commits()

if not bootstrap and not safe(["git", "status", "--porcelain"]):
    info("Nothing to commit.")
    show_repo_dashboard()
    sys.exit(0)

# ==========================================================
# version (UNCHANGED)
# ==========================================================
last = "v0.0.0" if bootstrap else safe(["git", "describe", "--tags", "--abbrev=0"]) or "v0.0.0"
m = re.match(r"v(\d+)\.(\d+)\.(\d+)", last)
major, minor, patch = map(int, m.groups()) if m else (0, 0, 0)
next_version = next_free_version(major, minor, patch)

# ==========================================================
# identity (UNCHANGED)
# ==========================================================
name, email, source = read_identity()
if source == "none":
    name, email = prompt_identity("", "")
    source = "prompted"

# ==========================================================
# stage (UNCHANGED)
# ==========================================================
run(["git", "add", "."])
files = safe(["git", "diff", "--cached", "--name-only"]).splitlines()
if not files:
    info("No staged changes.")
    show_repo_dashboard()
    sys.exit(0)

# ==========================================================
# model + timeout (UNCHANGED)
# ==========================================================
models = list_llm_models()
model_id = git_config("gup.model")
timeout = clamp_timeout(git_config("gup.timeout"))

model = next((m for m in models if m["id"] == model_id), None)
if not model:
    model = pick_model(models)
    git_config_set("gup.model", model["id"])

# ==========================================================
# commit message generation (UNCHANGED)
# ==========================================================
commit_msg = (
    "Initial commit" if bootstrap else
    "Update project configuration" if len(files) == 1 else
    f"Update {len(files)} project files"
)

def generate_message():
    diff = safe(["git", "diff", "--cached", "--unified=0"])[:15000]
    prompt = f"""Improve this Git commit message.

Rules:
- FIRST line ≤ 72 characters.
- Do NOT invent details.

Current message:
{commit_msg}

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
        out, err = p.communicate(timeout=int(timeout))
        if out.strip():
            return enforce_summary_limit(out.strip()), None
        return commit_msg, err.strip() or "AI returned empty output"
    except subprocess.TimeoutExpired:
        return commit_msg, "AI request timed out"
    except Exception as e:
        return commit_msg, str(e)

commit_msg, ai_warning = generate_message()

if ai_warning:
    warn("\n⚠ AI commit message generation failed")
    warn(f"Reason: {ai_warning}")
    warn(f"Model: {model['id']} | Timeout: {timeout}s\n")

# ==========================================================
# review loop (COSMETIC ONLY)
# ==========================================================
while True:
    header("GUP :: REVIEW")

    section("IDENTITY")
    kv("Name", name)
    kv("Email", email)
    kv("Source", source)

    section("RELEASE")
    kv("Version", next_version)
    kv("Model", f"{model['id']} ({timeout}s)")

    section("MESSAGE")
    print(f"\n{WHITE}{commit_msg}{RESET}\n")

    print(f"{CYAN}1){RESET} Commit & push")
    print(f"{CYAN}2){RESET} Edit identity")
    print(f"{CYAN}3){RESET} Edit message")
    print(f"{CYAN}4){RESET} Cancel")

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
        sys.exit(0)

# ==========================================================
# final commit (UNCHANGED)
# ==========================================================
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
subprocess.check_call(["git", "tag", "-a", next_version, "-m", final_msg])

branch = safe(["git", "branch", "--show-current"]) or "main"
run(["git", "push", "-u", "origin", branch])
run(["git", "push", "origin", next_version])

success(f"Released {next_version}")

