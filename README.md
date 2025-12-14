# gup

**gup** is a conservative Git helper that stages changes, generates a high-quality
commit message using an LLM, versions the release, tags it, and pushes safely —
all with an explicit human review step.

It is designed to be fast, predictable, and hard to misuse.

---

## What gup does

When you run `gup` inside a Git repository, it:

- stages current changes
- generates a concise commit message (AI-assisted)
- enforces a ≤72-character summary line
- proposes the next semantic version tag
- lets you review and edit everything
- creates the commit and annotated tag
- pushes the commit and tag to the remote

Nothing happens without your confirmation.

---

## Requirements

- Python ≥ 3.9
- Git
- The `llm` CLI installed and configured with at least one model
- A non-bare Git repository

---

## Installation

### Recommended: pip

This installs `gup` as a command available on your PATH.

    pip install gup

After installation, verify:

    gup

---

### Alternative: run without installing

From a cloned repository:

    python -m gup

This is useful for development or testing.

---

## Usage

From inside a Git repository:

    gup

That’s it.

You will be guided through:
- identity confirmation
- model selection (first run only)
- commit message review
- release confirmation

---

## Configuration

gup stores configuration in Git config:

- `gup.model`   – selected LLM model
- `gup.timeout` – AI request timeout (seconds)

These settings are repository-local and do not affect other projects.

---

## Safety guarantees

- gup will **not** commit if there are no staged changes
- gup will **not** rewrite history
- gup enforces timeouts on AI calls
- `import gup` has no side effects
- all commits and tags are explicit and reviewable

---

## Philosophy

gup favors:
- boring defaults
- visible state
- explicit confirmation
- small, reversible actions

It is opinionated, deliberately.

---

## License

MIT
