#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Get Git hooks directory
if [ -d ".git" ]; then
    # Running from project root
    HOOKS_DIR=".git/hooks"
elif [ -d "$PROJECT_ROOT/.git" ]; then
    # Running from another directory
    HOOKS_DIR="$PROJECT_ROOT/.git/hooks"
else
    echo -e "${RED}Error: .git directory not found${NC}"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Function to install a hook
install_hook() {
    local hook_name=$1
    local source="$PROJECT_ROOT/scripts/git-hooks/$hook_name"
    local target="$HOOKS_DIR/$hook_name"

    if [ -f "$source" ]; then
        cp "$source" "$target"
        chmod +x "$target"
        echo -e "${GREEN}✓${NC} Installed $hook_name hook"
        return 0
    else
        echo -e "${RED}✗${NC} Hook $hook_name not found in $PROJECT_ROOT/scripts/git-hooks"
        return 1
    fi
}

# Create pre-commit hook if it doesn't exist
if [ ! -f "$PROJECT_ROOT/scripts/git-hooks/pre-commit" ]; then
    mkdir -p "$PROJECT_ROOT/scripts/git-hooks"
    cat > "$PROJECT_ROOT/scripts/git-hooks/pre-commit" << 'EOF'
#!/bin/bash

# Get the project root directory
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# Run validation script
python "$PROJECT_ROOT/scripts/validate_config.py"
if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Please fix the errors and try again."
    exit 1
fi

# Run template verification
python "$PROJECT_ROOT/scripts/verify_templates.py"
if [ $? -ne 0 ]; then
    echo "❌ Template verification failed. Please fix the errors and try again."
    exit 1
fi

echo "✅ Pre-commit checks passed!"
exit 0
EOF
    chmod +x "$PROJECT_ROOT/scripts/git-hooks/pre-commit"
fi

# Get start time in milliseconds
start_time=$(($(date +%s%N)/1000000))
had_error=0

# Import Python monitoring
export PYTHONPATH=/Users/allan/Projects/iota
python3 -c "from server.core.monitor import monitor"

# Install hooks
echo "Installing Git hooks..."
install_hook "pre-commit"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Git hooks installed successfully!${NC}"
else
    had_error=1
    echo -e "\n${RED}Failed to install Git hooks${NC}"
fi

# Calculate duration and record metrics
end_time=$(($(date +%s%N)/1000000))
duration_ms=$((end_time - start_time))

python3 -c "from server.core.monitor import monitor; monitor.record_hook_installation($duration_ms, bool($had_error))"

exit $had_error
