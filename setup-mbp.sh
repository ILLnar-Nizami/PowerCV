#!/bin/bash
set -euo pipefail

# =============================================================================
# PowerCV — MacBook Pro (Apple Silicon) Bootstrap
# =============================================================================
# One-time setup script that:
#   1. Checks prerequisites (brew, docker, python, node, uv)
#   2. Clones and builds turboquant with Metal support
#   3. Downloads Qwen3.5-9B GGUF (Q4_K_M)
#   4. Creates Python venv and installs deps
#   5. Installs frontend npm deps
#   6. Starts Docker infra
# =============================================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[i]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

MODELS_DIR="${HOME}/models"
TURBOQUANT_DIR="${HOME}/code/llama-cpp-turboquant"
QWEN_URL="https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-UD-Q4_K_M.gguf"
QWEN_PATH="${MODELS_DIR}/Qwen3.5-9B-Q4_K_M.gguf"
VENV=".venv-mbp"

# ── Step 1: Check prerequisites ─────────────────────────────────────────────

info "Checking prerequisites..."

command -v brew >/dev/null 2>&1 || { err "Homebrew required: https://brew.sh"; exit 1; }
command -v docker >/dev/null 2>&1 || { err "Docker required: brew install --cask docker"; exit 1; }
command -v python3 >/dev/null 2>&1 || { err "Python 3 required: brew install python@3.12"; exit 1; }
command -v node >/dev/null 2>&1 || { err "Node.js required: brew install node"; exit 1; }
command -v uv >/dev/null 2>&1 || {
    info "Installing uv (fast Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
}

ok "All prerequisites met"

# ── Step 2: Build turboquant ────────────────────────────────────────────────

if [ -f "${TURBOQUANT_DIR}/build/bin/llama-server" ]; then
    ok "turboquant already built"
else
    info "Setting up turboquant..."
    mkdir -p "$(dirname "${TURBOQUANT_DIR}")"
    if [ ! -d "${TURBOQUANT_DIR}" ]; then
        git clone https://github.com/TheTom/llama-cpp-turboquant.git "${TURBOQUANT_DIR}"
    fi
    cd "${TURBOQUANT_DIR}"
    cmake -B build -DLLAMA_METAL=ON
    cmake --build build -j "$(sysctl -n hw.logicalcpu)"
    ok "turboquant built with Metal support"
fi

# ── Step 3: Download Qwen3.5-9B ─────────────────────────────────────────────

if [ -f "${QWEN_PATH}" ]; then
    ok "Qwen3.5-9B GGUF already downloaded (${QWEN_PATH})"
else
    info "Downloading Qwen3.5-9B (Q4_K_M) GGUF (~6.5GB)..."
    mkdir -p "${MODELS_DIR}"
    echo "  URL: ${QWEN_URL}"
    echo "  To:  ${QWEN_PATH}"
    echo ""
    echo "  You can download manually with:"
    echo "    curl -L -o '${QWEN_PATH}' '${QWEN_URL}'"
    echo ""
    echo "  Or using huggingface-cli:"
    echo "    pip install huggingface-hub"
    echo "    huggingface-cli download unsloth/Qwen3.5-9B-GGUF Qwen3.5-9B-UD-Q4_K_M.gguf --local-dir '${MODELS_DIR}'"
    echo ""

    # Offer to download via huggingface-cli if available
    if command -v huggingface-cli >/dev/null 2>&1; then
        huggingface-cli download unsloth/Qwen3.5-9B-GGUF \
            Qwen3.5-9B-UD-Q4_K_M.gguf \
            --local-dir "${MODELS_DIR}"
        # Create a symlink with the shorter name
        ln -sf "${MODELS_DIR}/Qwen3.5-9B-UD-Q4_K_M.gguf" "${QWEN_PATH}"
        ok "Qwen3.5-9B downloaded"
    else
        echo ""
        echo "  Install huggingface-cli for automatic download:"
        echo "    pip install huggingface-hub"
        echo "  Then re-run this script."
    fi
fi

# ── Step 4: Python venv ─────────────────────────────────────────────────────

if [ -d "${VENV}" ]; then
    ok "Python venv already exists (${VENV})"
else
    info "Creating Python virtual environment..."
    python3 -m venv "${VENV}"
    source "${VENV}/bin/activate"
    pip install --upgrade pip uv
    uv pip install -r requirements.txt
    uv pip install -r requirements-dev.txt
    ok "Python dependencies installed"
fi

# ── Step 5: Frontend deps ───────────────────────────────────────────────────

if [ -d "frontend/node_modules" ]; then
    ok "Frontend dependencies already installed"
else
    info "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
    ok "Frontend dependencies installed"
fi

# ── Step 6: Docker infra ────────────────────────────────────────────────────

info "Starting Docker infrastructure (MongoDB, Redis, PostgreSQL)..."
docker compose -f docker-compose.infra.yml up -d

info "Waiting for services to be healthy..."
for i in $(seq 1 15); do
    sleep 2
    if docker compose -f docker-compose.infra.yml ps --format json 2>/dev/null | grep -q '"Health"' 2>/dev/null; then
        break
    fi
done
docker compose -f docker-compose.infra.yml ps
ok "Docker infra is running"

# ── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  PowerCV MBP Setup Complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Start the LLM:"
echo "    ${TURBOQUANT_DIR}/build/bin/llama-server \\"
echo "      -m ${QWEN_PATH} \\"
echo "      --host 0.0.0.0 --port 8080 -ngl 32"
echo ""
echo "  Or:   make -f Makefile.mbp run-llm"
echo ""
echo "  Start backend:  source ${VENV}/bin/activate"
echo "                  export \$(grep -v '^#' .env.mbp | xargs)"
echo "                  uvicorn app.main:app --reload --host 0.0.0.0 --port 8081"
echo ""
echo "  Or:   make -f Makefile.mbp run-be"
echo ""
echo "  Start frontend: cd frontend && npm run dev"
echo ""
echo "  Or:   make -f Makefile.mbp run-fe"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
