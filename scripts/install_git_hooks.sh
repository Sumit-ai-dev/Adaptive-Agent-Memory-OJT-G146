#!/usr/bin/env bash
# Install Git pre-commit hook for Gitleaks secret scanning
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_PATH="${REPO_ROOT}/.git/hooks/pre-commit"

echo "Installing Gitleaks pre-commit hook into ${HOOK_PATH}..."

cat << 'EOF' > "${HOOK_PATH}"
#!/usr/bin/env bash
# Pre-commit hook: Block commits containing leaked secrets
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v gitleaks &> /dev/null; then
    echo "⚠️  [Gitleaks] Warning: 'gitleaks' binary is not installed on PATH."
    echo "   Install via: brew install gitleaks (macOS) or see https://github.com/gitleaks/gitleaks"
    echo "   Skipping local secret pre-commit scan..."
    exit 0
fi

echo "🔒 [Gitleaks] Scanning staged changes for secrets..."
gitleaks protect --staged --verbose --config .gitleaks.toml

if [ $? -ne 0 ]; then
    echo "❌ [Gitleaks] Commit aborted: Secret or credential detected in staged files."
    echo "   Please remove the secret before committing."
    exit 1
fi
EOF

chmod +x "${HOOK_PATH}"
echo "✅ Gitleaks pre-commit hook installed successfully."
