# gup

**gup** is a calm, repo-aware Git release helper that stages changes, generates commit messages with an LLM (optionally), tags versions, and pushes — while always keeping the human in control.

It is designed for developers who:
- work on many repositories
- care about clean Git history
- want AI assistance without losing determinism
- want repo-local configuration, not global side effects

`gup` is intentionally boring, explicit, and inspectable.

---

## Why gup exists

Typical Git workflows break down in one of two ways:

1. **Too manual**  
   People forget to tag, version, or review identity.
2. **Too automated**  
   Tools commit with the wrong author, wrong message, or hidden defaults.

`gup` sits in the middle:
- It automates the *mechanics*
- It never skips the *review*

---

## Core principles

- **Repo-local state only**  
  All decisions (identity, AI model, timeout) live in the repository’s Git config.
- **Human-visible defaults**  
  Nothing is committed without a preview screen.
- **AI is optional and bounded**  
  AI assists with commit messages but never blocks or invents facts.
- **Safe shell usage**  
  No user content is passed through `shell=True`.
- **Predictable behavior**  
  Running `gup` when nothing has changed is still useful.

---

## Dependencies

### Required

- **Python 3.10+**
- **Git**

Check versions:

```bash
python3 --version
git --version
```

---

### Optional (for AI-assisted commit messages)

- **`llm` CLI**  
  https://github.com/simonw/llm

`gup` will work **without** `llm`.  
If `llm` is not installed or fails, `gup` falls back to deterministic commit messages and continues safely.

Install `llm`:

```bash
pipx install llm
```

(or inside a virtual environment)

Verify:

```bash
llm models
```

---

## Installation

### 1. Install the script

Place the `gup` script somewhere on your system, for example:

```bash
sudo install -m 755 gup /usr/local/bin/gup
```

This does **three important things**:
- Copies the script to a standard executable location
- Sets executable permissions
- Makes `gup` available system-wide

---

### 2. Ensure `/usr/local/bin` is in your PATH

Most Linux and macOS systems already include it.

Check:

```bash
echo $PATH | tr ':' '\n' | grep /usr/local/bin
```

If nothing is printed, add it.

For **bash**:

```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

For **zsh**:

```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

### 3. Verify installation

From **any directory**:

```bash
gup
```

Expected behavior:
- Outside a Git repo → informative message
- Inside a Git repo → dashboard or commit flow

---

## Usage

From inside any Git repository:

```bash
gup
```

No flags required for normal use.

---

## What gup does

### When there are changes

1. Stages all changes
2. Determines the next semantic version (`vX.Y.Z`)
3. Generates a commit message:
   - Deterministic fallback first
   - AI improvement if enabled and available
   - Summary line enforced to ≤ 72 characters
4. Shows a **review screen**:
   - Commit identity
   - Version
   - AI model + timeout
   - Commit message
5. Allows you to:
   - Edit identity
   - Edit message
   - Change AI model and regenerate
6. Commits, tags, and pushes safely

---

### When there are no changes

`gup` shows a **repository dashboard**:

- Repo-local identity (with source)
- Default AI model and timeout
- Current branch
- Latest tag
- Remotes
- Working tree status
- Last 3 commits

This makes `gup` useful even when idle.

---

## AI configuration (repo-local)

All AI settings are stored **per repository** using Git config:

```bash
git config gup.model
git config gup.timeout
```

Example:

```bash
git config gup.model gpt-5-mini
git config gup.timeout 20
```

- `gup.model` → canonical model ID (not label)
- `gup.timeout` → seconds (max 60)

If a model exists, `gup` uses it **without prompting**.

---

## Identity handling

`gup` follows strict precedence:

1. Repo-local identity
2. Global identity
3. Prompt only if neither exists

If identity is edited during review:
- It is written to **repo config only**
- Global Git identity is never modified

This supports:
- multi-user machines
- multiple projects per user
- project-specific commit identities

---

## Safety guarantees

- No multi-line user content is passed through the shell
- Git commands with user input use argument lists
- Commit messages are never executed
- Annotated tags are created safely
- AI failures never abort commits

---

## Philosophy

`gup` is intentionally not clever.

It prefers:
- clarity over magic
- inspection over automation
- reproducibility over convenience

If something goes wrong, you should be able to:
- see it
- understand it
- fix it without surprises

---

## Non-goals

- Replacing Git
- Enforcing commit conventions
- Managing branches
- Acting without confirmation
- Hiding versioning decisions

---

## License

MIT

---
