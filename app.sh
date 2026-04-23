#!/bin/bash
set -e

# ============================================
# PowerCV - Startup Script
# ============================================
# Usage:
#   ./app.sh start       Start all services
#   ./app.sh stop        Stop all services  
#   ./app.sh restart    Restart all services
#   ./app.sh status     Show status
#   ./app.sh logs       Show docker logs
#   ./app.sh logs rt    Stream logs in real time
#   ./app.sh rebuild   Rebuild containers
#   ./app.sh rebuild --no_cache  Rebuild without cache
#   ./app.sh help       Show help
#
# Environment variables:
#   FRONTEND_PORT    Frontend port (default: 3333)
#   BACKEND_PORT     Backend port (default: 8081)
#   POSTGRES_PORT    PostgreSQL port (default: 5432)
#   REDIS_PORT       Redis port (default: 6379)
#   MONGODB_PORT     MongoDB port (default: 27018)
# ============================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

# Default ports
FRONTEND_PORT="${FRONTEND_PORT:-3333}"
BACKEND_PORT="${BACKEND_PORT:-8081}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
MONGODB_PORT="${MONGODB_PORT:-27018}"

show_usage() {
    print_banner
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services (docker, db, redis, fe, be)"
    echo "  stop            Stop all services"
    echo "  restart        Restart all services"
    echo "  status         Show service status"
    echo "  logs           Show docker logs (last 100 lines)"
    echo "  logs rt        Stream logs in real time"
    echo "  rebuild        Rebuild docker images (with cache)"
    echo "  rebuild --no_cache  Rebuild without cache"
    echo "  help           Show this help"
    echo ""
    echo "Environment variables:"
    echo "  FRONTEND_PORT    Frontend port (default: 3333)"
    echo "  BACKEND_PORT     Backend port (default: 8081)"
    echo "  POSTGRES_PORT    PostgreSQL port (default: 5432)"
    echo "  REDIS_PORT       Redis port (default: 6379)"
    echo "  MONGODB_PORT    MongoDB port (default: 27018)"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  FRONTEND_PORT=3000 BACKEND_PORT=8000 $0 start"
    echo "  $0 logs rt"
    echo "  $0 rebuild --no_cache"
}

print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'

 █████╗ ███████╗███████╗██╗   ██╗███╗   ███╗███████╗
██╔══██╗██╔════╝██╔════╝██║   ██║████╗ ████║██╔════╝
███████║█████╗  ███████╗██║   ██║██╔████╔██║█████╗
██╔══██║██╔══╝  ╚════██║██║   ██║██║╚██╔╝██║██╔══╝
██║  ██║███████╗███████║╚██████╔╝██║ ╚═╝ ██║███████╗
╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝

 ██████╗ ███╗   ██╗███████╗███████╗██╗     ██╗██╗  ██╗
██╔════╝██╣██╗  ██║██╔════╝██╔════╝██║     ██║╚██╗██╔╝
██║     ██║╚██╗██║███████╗█████╗  ██║     ██║ ╚███╔╝ 
██║     ██║ ╚████║██╔════╝██╔══╝  ██║     ██║ ██╔██╗ 
╚██████╗██║  ╚██║███████║███████╗███████╗██║██╗╚████║
 ╚═════╝╚═╝   ╚═╝╚══════╝╚══════╝╚══════╝╚═╝╚═╝ ╚═══╝

EOF
    echo -e "${NC}"
    echo -e "${BOLD}        PowerCV - Resume Builder & Optimizer${NC}"
    echo ""
}

status() { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${BLUE}[i]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

start() {
    print_banner
    
    echo "Port Configuration:"
    echo -e "  ${BOLD}Frontend:${NC}   $FRONTEND_PORT"
    echo -e "  ${BOLD}Backend:${NC}    $BACKEND_PORT"
    echo -e "  ${BOLD}PostgreSQL:${NC} $POSTGRES_PORT"
    echo -e "  ${BOLD}Redis:${NC}      $REDIS_PORT"
    echo -e "  ${BOLD}MongoDB:${NC}     $MONGODB_PORT"
    echo ""
    
    info "Starting Docker services..."
    
    # Set environment for docker-compose
    export FRONTEND_PORT
    export BACKEND_PORT
    export POSTGRES_PORT
    export REDIS_PORT
    export MONGODB_PORT
    
    # Start all services
    docker compose up -d
    
    info "Waiting for services to be ready..."
    
    # Wait for backend health
    for i in {1..60}; do
        if curl -s "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
            status "Backend is ready"
            break
        fi
        if [ $i -eq 60 ]; then
            error "Backend failed to start within 60 seconds"
            echo "Run './app.sh logs' to see what's wrong"
            exit 1
        fi
        sleep 1
    done
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    status "PowerCV is running!"
    echo ""
    echo -e "  ${BOLD}Frontend:${NC}   http://localhost:${FRONTEND_PORT}"
    echo -e "  ${BOLD}Backend:${NC}    http://localhost:${BACKEND_PORT}"
    echo -e "  ${BOLD}API Docs:${NC}  http://localhost:${BACKEND_PORT}/docs"
    echo -e "  ${BOLD}PostgreSQL:${NC} localhost:${POSTGRES_PORT}"
    echo -e "  ${BOLD}Redis:${NC}      localhost:${REDIS_PORT}"
    echo -e "  ${BOLD}MongoDB:${NC}     localhost:${MONGODB_PORT}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    info "Run './app.sh logs' to view logs"
    info "Run './app.sh stop' to stop everything"
    echo ""
}

stop() {
    info "Stopping all services..."
    docker compose down
    status "All services stopped"
}

restart() {
    stop
    sleep 2
    start
}

status_cmd() {
    echo "Service Status:"
    echo ""
    docker compose ps
}

logs() {
    docker compose logs -f --tail=100
}

logs_rt() {
    docker compose logs -f
}

build() {
    local no_cache=""
    if [ "$1" = "--no_cache" ]; then
        no_cache="--no-cache"
        info "Building Docker images without cache..."
    else
        info "Building Docker images..."
    fi
    docker compose build $no_cache
    status "Build complete"
}

# Parse command
COMMAND="${1:-}"

case "$COMMAND" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status_cmd ;;
    logs)
        if [ "$2" = "rt" ]; then
            logs_rt
        else
            logs
        fi
        ;;
    logs_rt) logs_rt ;;
    rebuild)
        if [ "$2" = "--no_cache" ]; then
            build --no_cache
        else
            build
        fi
        ;;
    help|--help|-h) show_usage ;;
    *) error "Unknown or missing command: $COMMAND"; show_usage; exit 1 ;;
esac