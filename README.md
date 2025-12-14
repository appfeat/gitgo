# gup Release 0.1.0

**gup** (Git Update & Push) is a command-line tool that helps you commit, version, and push Git
changes safely, with a clear review step and optional AI-assisted commit
messages.

If you often forget to write good commit messages, tag releases consistently,
or want a single, predictable command to finalize your work, gup is designed
for you.

---

## What problem does gup solve?

Many Git workflows break down at the same points:

- changes pile up without commits
- commit messages are rushed or inconsistent
- version tags are forgotten or misnumbered
- pushes happen without a final review

gup turns these scattered steps into a **single, guided release flow**.

---

## What gup does

When run inside a Git repository, `gup`:

- stages current changes
- proposes a clear commit message (optionally AI-assisted)
- enforces a clean, ≤72-character summary line
- determines the next version tag automatically
- shows a full review screen before committing
- creates the commit and annotated tag
- pushes both to the configured remote

Every step is visible. Nothing happens without confirmation.

---

## Why gup is different

gup is intentionally conservative.

- No history rewriting
- No hidden automation
- No background hooks
- No silent commits

It favors **clarity over cleverness** and **review over speed**.

---

## Requirements

- Python 3.9 or newer
- Git
- The `llm` CLI installed and configured (for AI commit messages)
- A non-bare Git repository

---

## Installation

### Using pip (recommended)

Install gup as a standard CLI tool:

    git clone git@github.com:appfeat/gup.git
    cd gup 
    pip install .

After installation, the `gup` command will be available on your PATH.

---

## Usage

From inside a Git repository:

    gup

That’s the entire interface.

gup will guide you through:
- identity confirmation (if needed)
- model selection (first run only)
- commit message review
- release confirmation

---

## Configuration

gup stores its settings in Git config:

- `gup.model`   – selected LLM model
- `gup.timeout` – AI request timeout (seconds)

These settings are repository-local and do not affect other projects.

---

## Typical use cases

- finishing a feature and creating a clean release commit
- maintaining consistent version tags
- solo development with better commit hygiene
- small teams that want predictable Git history

---

## Philosophy

gup is designed around a simple idea:

> Finishing work should feel deliberate, not rushed.

It aims to make the *last step* of development calm, reviewable, and reliable.

---

## License

MIT
