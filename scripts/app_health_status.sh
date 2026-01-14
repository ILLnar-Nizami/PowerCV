#!/bin/bash

echo "🚀 PowerCV Application Health Status"
echo "===================================="

# Check if key directories exist
echo "📁 Checking project structure..."
dirs_to_check=("frontend" "app" "data" "scripts" "tests")
for dir in "${dirs_to_check[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir directory exists"
    else
        echo "❌ $dir directory not found"
    fi
done

# Check database connectivity
echo ""
echo "🗄️  Checking database..."
if command -v mongosh &> /dev/null; then
    # Try to connect to MongoDB
    if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        echo "✅ MongoDB connection successful"
    else
        echo "❌ MongoDB connection failed"
    fi
else
    echo "⚠️  mongosh not found, skipping DB check"
fi

# Check if services are running
echo ""
echo "🔧 Checking services..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Docker services are running"
else
    echo "❌ No Docker services running"
fi

# Check Python environment
echo ""
echo "🐍 Checking Python environment..."
if command -v python &> /dev/null && python -c "import fastapi, pydantic" &> /dev/null; then
    echo "✅ Python dependencies installed"
else
    echo "❌ Python dependencies missing"
fi

# Check frontend build
echo ""
echo "⚛️  Checking frontend..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    if npm run build > /dev/null 2>&1; then
        echo "✅ Frontend build successful"
    else
        echo "❌ Frontend build failed"
    fi
    cd ..
else
    echo "❌ Frontend not properly set up"
fi

# Check test status
echo ""
echo "🧪 Checking tests..."
if [ -d "tests" ] && [ -f "pyproject.toml" ]; then
    if poetry run pytest --collect-only > /dev/null 2>&1; then
        echo "✅ Tests can be collected"
    else
        echo "❌ Test collection failed"
    fi
else
    echo "❌ Test setup incomplete"
fi

echo ""
echo "🎯 Application Health Status Check Complete"
echo ""
echo "You can run:"
echo "  ./scripts/run.sh test     # Run full test suite"
echo "  ./scripts/run.sh dev      # Start development servers"
echo "  docker-compose up         # Start all services"
echo ""
echo "📊 For detailed metrics, run individual checks above"
