#!/bin/bash
# setup_dev.sh - Development environment setup script for PowerCV

set -e  # Exit on error

echo "Setting up PowerCV development environment..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies with Poetry
echo "Installing dependencies with Poetry..."
poetry install

# Install pre-commit hooks if config exists
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Installing pre-commit hooks..."
    poetry run pre-commit install
fi

echo "Development environment setup complete!"
echo "---------------------------------------"
echo "To activate the virtual environment, run:"
echo "    poetry shell"
echo ""
echo "To run the application:"
echo "    ./scripts/run.sh"
echo ""
echo "To run tests:"
echo "    poetry run pytest"