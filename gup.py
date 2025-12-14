#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import datetime

# ==========================================================
# gup — final, boring, trustworthy (dashboard enriched)
# ==========================================================

BLUE="\033[34m"; GREEN="\033[32m"; YELLOW="\033[33m"
CYAN="\033[36m"; BOLD="\033[1m"; RESET="\033[0m"

# ---------------- helpers ----------------
def run(cmd, capture=False, env=None):
    if capture:
        return subprocess.check_output(cmd, shell=True, text=True, env=env).strip()
    subprocess.check_call(cmd, shell=True, env=env)

def safe(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""

def has_commits():
    return bool(safe("git rev-parse --verify HEAD"))

def enforce_summary_limit(msg, limit=72):
    lines = msg.strip().splitlines()
    if not lines:
        return msg
    summary = lines[0]
    if len(summary) <= limit:
        return msg
    cut = summary[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    lines[0] = cut
    return "\n".join(lines)

# ---------------- identity ----------------
def read_identity():
    n = safe("git config user.name")
    e = safe("git config user.email")
    if n or e:
        return n, e, "repo"
    n = safe("git config --global user.name")
    e = safe("git config --global user.email")
    if n or e:
        return n, e, "global"
    return "", "", "none"

def prompt_identity(n, e):
    print("\nEnter commit identity (blank keeps current):")
    return (
        input(f"Name [{n}]: ").strip() or n,
        input(f"Email [{e}]: ").strip() or e,
    )

# ---------------- dashboard ----------------
def show_repo_dashboard():
    name, email, source = read_identity()
    model = safe("git config gup.model")

    print("\nRepository status")
    print("────────────────────────────────")

    print("Identity:")
    print(f"  Name:   {name or '(not set)'}")
    print(f"  Email:  {email or '(not set)'}")
    print(f"  Source: {source}")

    print("\nAI:")
    print(f"  Default model: {model if model else '(not set)'}")

    branch = safe("git branch --show-current") or "(detached)"
    print(f"\nBranch:     {branch}")

    tag = safe("git describe --tags --abbrev=0")
    if tag:
        print(f"Latest tag: {tag}")

    print("\nRemotes:")
    remotes = safe("git remote -v")
    print(remotes if remotes else "  (none)")

    status = safe("git status --short")
    print("\nWorking tree:")
    print("✔ Clean" if not status else status)

    print("\nRecent commits:")
    log = safe("git log -3 --pretty=format:'%h | %ad | %s' --date=short")
    print(log if log else "  (no commits yet)")
    print()

# ---------------- models ----------------
def list_llm_models():
    out = safe("llm models")
    models = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.endswith(":"):
            continue
        label = line
        core = line.split("(", 1)[0].strip()
        model_id = core.split(":")[-1].strip()
        models.append({"id": model_id, "label": label})
    return models

def model_score(m):
    name = m["id"]
    score = 0
    score += 1000 if "gemini" in name else 500
    v = re.search(r"(\d+)\.(\d+)", name)
    if v:
        score += int(v.group(1))*100 + int(v.group(2))*10
    if "flash" in name:
        score += 50
    if "lite" in name or "mini" in name:
        score += 30
    return score

def read_saved_model():
    return safe("git config gup.model")

# ==========================================================
# repo check
# ==========================================================
if safe("git rev-parse --is-inside-work-tree") != "true":
    print("Not inside a Git repository.")
    sys.exit(1)

bootstrap = not has_commits()

# ---- clean repo path ----
if not bootstrap and not safe("git status --porcelain"):
    print("Nothing to commit.")
    show_repo_dashboard()
    sys.exit(0)

# ==========================================================
# version
# ==========================================================
last = "v0.0.0" if bootstrap else safe("git describe --tags --abbrev=0") or "v0.0.0"
m = re.match(r"v(\d+)\.(\d+)\.(\d+)", last)
major, minor, patch = map(int, m.groups()) if m else (0,0,0)
next_version = f"v{major}.{minor}.{patch+1}"

# ==========================================================
# identity
# ==========================================================
name, email, source = read_identity()
if source == "none":
    name, email = prompt_identity("", "")
    source = "prompted"

# ==========================================================
# stage
# ==========================================================
run("git add .")
files = safe("git diff --cached --name-only").splitlines()
if not files:
    print("No staged changes.")
    show_repo_dashboard()
    sys.exit(0)

# ==========================================================
# model selection
# ==========================================================
models = list_llm_models()
saved_id = read_saved_model()
saved_model = next((m for m in models if m["id"] == saved_id), None)

gemini = [m for m in models if "gemini" in m["id"]]
openai = [m for m in models if "gemini" not in m["id"]]

best_gemini = max(gemini, key=model_score) if gemini else None
best_openai = max(openai, key=model_score) if openai else None

options = []
if saved_model:
    options.append(saved_model)
for m in (best_gemini, best_openai):
    if m and m not in options:
        options.append(m)
options = options[:2]

print("\nAI model:")
for i,m in enumerate(options,1):
    tag = " (default)" if i == 1 else ""
    print(f" {i}) {m['label']}{tag}")
print(" 3) More models...")

choice = input("Select model [default]: ").strip()

if choice == "3":
    print("\nAll models:")
    for i,m in enumerate(models,1):
        print(f" {i}) {m['label']}")
    c = input("Select model: ").strip()
    model = models[int(c)-1] if c.isdigit() and 1<=int(c)<=len(models) else options[0]
elif choice.isdigit() and 1<=int(choice)<=len(options):
    model = options[int(choice)-1]
else:
    model = options[0]

run(f'git config gup.model "{model["id"]}"')

# ==========================================================
# commit message
# ==========================================================
if bootstrap:
    commit_msg = "Initial commit"
elif len(files) == 1:
    commit_msg = "Update project configuration"
elif len(files) <= 5:
    commit_msg = f"Update {len(files)} project files"
else:
    commit_msg = f"Update multiple project files ({len(files)})"

ai_warning = None
diff = safe("git diff --cached --unified=0")[:15000]
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
    out, err = p.communicate(timeout=12)
    if out.strip():
        commit_msg = out.strip()
    elif err.strip():
        ai_warning = err.strip()
    else:
        ai_warning = "AI returned empty output"
except subprocess.TimeoutExpired:
    ai_warning = "AI request timed out"
except Exception as e:
    ai_warning = str(e)

commit_msg = enforce_summary_limit(commit_msg)

if ai_warning:
    print(f"\n{YELLOW}⚠️ AI commit message generation failed{RESET}")
    print(f"{YELLOW}   Reason: {ai_warning}{RESET}")
    print(f"{YELLOW}   Model: {model['id']}{RESET}\n")

# ==========================================================
# review loop
# ==========================================================
while True:
    print(f"\n{BOLD}Identity:{RESET} {name} <{email}> [{source}]")
    print(f"{BOLD}Version:{RESET} {next_version}")
    print(f"{BOLD}Model:{RESET}   {model['label']}")
    print(f"\n{BOLD}Message:{RESET}\n{commit_msg}\n")
    print("1) Commit & push\n2) Edit identity\n3) Edit message\n4) Cancel")
    c = input("Choice: ").strip()
    if c == "1":
        break
    if c == "2":
        name,email = prompt_identity(name,email)
        run(f'git config user.name "{name}"')
        run(f'git config user.email "{email}"')
        source = "repo"
    if c == "3":
        print("Enter message (Ctrl+D):")
        commit_msg = enforce_summary_limit(sys.stdin.read().strip())
    if c == "4":
        sys.exit(0)

# ==========================================================
# final commit
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

subprocess.check_call(["git","commit","-m",final_msg], env=env)
run(f'git tag -a {next_version} -m "{final_msg}"')

branch = safe("git branch --show-current") or "main"
run(f"git push -u origin {branch}")
run(f"git push origin {next_version}")

print(f"{GREEN}Released {next_version}{RESET}")

