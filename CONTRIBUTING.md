# Contributing to AI-Me

Welcome! This document outlines the process for contributing to the AI-Me project.

## Prerequisites

If you want to propose changes to ai-me, please search our [issues](https://github.com/byoung/ai-me/issues) list first. If there is none, please create a new issue and label it as a bug or enhancement. Before you get started, let's have a conversation about the proposal! 

This project is transitioning to [Spec Kit](https://github.com/github/spec-kit), so any new features must first start with a `/speckit.specify` in order to establish our user stories and requirements consistently.

To develop on this project, you will need to:

- Set up [Docker](https://docs.docker.com/engine/install/) for container based development
- Set up [uv](https://docs.astral.sh/uv/getting-started/installation/) for local development
- Create a fork of [ai-me](https://github.com/byoung/ai-me)
- Configure git with [GPG signing configured](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key)
- Do a full review of our [constitution](/.specify/memory/constitution.md)
- Set up a [pre-commit hook](#setting-up-the-pre-commit-hook) to clear notebook output (unless you have the discipline to manually do it before opening PRs -- I (@byoung) do not...)

## Setup

### 1. Clone and Install Dependencies

```bash
git clone https://github.com/<your fork>
cd ai-me

# Local dev
uv sync

# Container dev
docker compose build notebooks
```

### 2. Environment Configuration

Create a `.env` file in the project root with required keys:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...

# Bot Identity
BOT_FULL_NAME="Ben Young"
APP_NAME="AI-Me"

# Optional: External Tools
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
LINKEDIN_API_TOKEN=...

# Optional: Remote Logging (Grafana Loki)
LOKI_URL=https://logs-prod-us-central1.grafana.net
LOKI_USERNAME=...
LOKI_PASSWORD=...
```

### 3. Start the application

```bash
# Local
uv run src/app.py  # Launches Gradio on default port

# Docker
docker compose up notebooks
```

### 4. Make changes

You don't have to use Spec Kit to plan and implement your specs, BUT you MUST create traceability between your spec, implementation, and tests per our [constitution](/.specify/memory/constitution.md)! 

### 5. Test

For detailed information on testing check out our [TESTING.md](/TESTING.md) guide.


### 6. Deploy

To deploy to HF, check out this [section](/README.md#deployment) in our README. This test ensures that your system is deployable and usable in HF.

### 7. Open a PR

Be sure to give a brief overview of the change and link it to the issue it's resolving.


## Setting Up the Pre-Commit Hook

A Git pre-commit hook automatically clears all Jupyter notebook outputs before committing. This keeps the repository clean and reduces diff noise by preventing output changes from cluttering commits.

### Installation

#### Option 1: Automated Installation (Recommended)

After cloning the repository, run:

```bash
cd ai-me
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Then create the hook script:

```bash
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook to clear Jupyter notebook outputs

# Find all staged .ipynb files
notebooks=$(git diff --cached --name-only --diff-filter=ACM | grep '\.ipynb$')

if [ -n "$notebooks" ]; then
    echo "Clearing outputs from notebooks..."
    for notebook in $notebooks; do
        if [ -f "$notebook" ]; then
            echo "  Processing: $notebook"
            # Clear outputs using Python directly (no jupyter dependency needed)
            python3 -c "
import json

notebook_path = '$notebook'

# Read the notebook
with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# Clear outputs from all cells
for cell in nb.get('cells', []):
    if cell['cell_type'] == 'code':
        cell['outputs'] = []
        cell['execution_count'] = None

# Write back the cleaned notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
    f.write('\n')
"
            # Re-stage the cleaned notebook
            git add "$notebook"
        fi
    done
    echo "✓ Notebook outputs cleared"
fi

exit 0
EOF
chmod +x .git/hooks/pre-commit
```

#### Option 2: Manual Installation

1. Navigate to your git hooks directory:
   ```bash
   cd .git/hooks
   ```

2. Create a new file called `pre-commit`:
   ```bash
   touch pre-commit
   chmod +x pre-commit
   ```

3. Open the file in your editor and paste the script above (starting with `#!/bin/bash`).

### Verification

To verify the hook is working, make a change to a notebook and stage it:

```bash
git add src/notebooks/experiments.ipynb
git commit -m "Test notebook commit"
```

You should see output like:
```
Clearing outputs from notebooks...
  Processing: src/notebooks/experiments.ipynb
✓ Notebook outputs cleared
```

**Note**: A Git pre-commit hook is installed at `.git/hooks/pre-commit` that automatically clears all notebook outputs before committing.

