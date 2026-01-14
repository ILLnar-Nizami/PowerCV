#!/bin/bash
# migration_status.sh - Database health and status check for PowerCV

echo "🔍 PowerCV Database Status"
echo "=========================="

# Check MongoDB connection
if command -v mongosh &> /dev/null; then
    echo "Checking MongoDB connection..."
    if mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
        echo "✅ MongoDB is connected"
        # Show database stats
        mongosh --eval "db.stats()" --quiet | head -10
    else
        echo "❌ MongoDB connection failed"
        exit 1
    fi
else
    echo "⚠️  mongosh not found, skipping MongoDB check"
fi

# Check Redis connection
if command -v redis-cli &> /dev/null; then
    echo ""
    echo "Checking Redis connection..."
    if redis-cli ping | grep -q PONG; then
        echo "✅ Redis is connected"
        # Show Redis info
        redis-cli info server | grep -E "(redis_version|uptime_in_days)"
    else
        echo "❌ Redis connection failed"
    fi
else
    echo "⚠️  redis-cli not found, skipping Redis check"
fi

echo ""
echo "🎯 Database status check complete"