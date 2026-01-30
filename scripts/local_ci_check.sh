#!/bin/bash

# Local CI simulation script
# This simulates what the GitHub Actions CI does

echo "🚀 Starting local CI simulation..."

echo "📦 Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo "🎨 Checking Black formatting..."
if python -m black --check --diff app/ scripts/ tests/; then
    echo "✅ Black formatting passed"
    BLACK_STATUS="passed"
else
    echo "❌ Black formatting failed"
    echo "🔧 Auto-fixing formatting issues..."
    python -m black app/ scripts/ tests/
    python -m isort app/ scripts/ tests/
    echo "📝 Files have been formatted"
    BLACK_STATUS="failed"
fi

echo "📚 Checking import ordering..."
if python -m isort --check-only --diff app/ scripts/ tests/; then
    echo "✅ Import ordering passed"
    ISORT_STATUS="passed"
else
    echo "❌ Import ordering failed"
    echo "🔧 Auto-fixing import issues..."
    python -m isort app/ scripts/ tests/
    echo "📝 Imports have been fixed"
    ISORT_STATUS="failed"
fi

echo "🔍 Running strict type checking on app/..."
if python -m mypy app/ --strict; then
    echo "✅ MyPy passed on app/"
    MYPY_APP_STATUS="passed"
else
    echo "❌ MyPy failed on app/"
    MYPY_APP_STATUS="failed"
fi

echo "🔍 Running relaxed type checking on scripts/..."
if python -m mypy scripts/ --ignore-missing-imports --no-strict-optional; then
    echo "✅ MyPy passed on scripts/"
    MYPY_SCRIPTS_STATUS="passed"
else
    echo "⚠️ MyPy failed on scripts/ but this is allowed"
    echo "📝 Scripts have relaxed type checking requirements"
    MYPY_SCRIPTS_STATUS="relaxed"
fi

echo ""
echo "📊 Summary:"
echo "- Black: $BLACK_STATUS"
echo "- isort: $ISORT_STATUS"
echo "- MyPy (app/): $MYPY_APP_STATUS"
echo "- MyPy (scripts/): $MYPY_SCRIPTS_STATUS"

if [[ "$BLACK_STATUS" == "failed" || "$ISORT_STATUS" == "failed" || "$MYPY_APP_STATUS" == "failed" ]]; then
    echo ""
    echo "❌ Some checks failed. Changes have been auto-fixed."
    echo "💡 Please commit the auto-fixed changes and run again."
    exit 1
else
    echo ""
    echo "✅ All checks passed!"
    exit 0
fi
