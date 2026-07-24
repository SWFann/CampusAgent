#!/bin/bash

# CampusAgent 工具版本检查脚本
# 用途：验证开发环境是否符合工具版本基线

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 版本检查结果
ERRORS=0
WARNINGS=0

echo "=================================="
echo "CampusAgent 工具版本检查"
echo "=================================="
echo ""

# 检查函数
check_version() {
    local tool=$1
    local version_cmd=$2
    local min_version=$3
    local current_version=$4

    echo -n "检查 $tool... "

    if [ -z "$current_version" ]; then
        echo -e "${RED}✗ 未安装${NC}"
        ((ERRORS++))
        return
    fi

    echo -e "${GREEN}✓${NC} $current_version"

    # 版本比较（简单实现）
    if [ "$tool" = "Docker" ] || [ "$tool" = "Docker Compose" ]; then
        # Docker 版本比较逻辑
        echo -e "  ${YELLOW}⚠ 请确保版本 >= $min_version${NC}"
        ((WARNINGS++))
    fi
}

# 1. Node.js
echo "【前端工具链】"
NODE_VERSION=$(node --version 2>/dev/null || echo "")
check_version "Node.js" "node --version" "v18" "$NODE_VERSION"

# 检查包管理器（推荐 pnpm）
PNPM_VERSION=$(pnpm --version 2>/dev/null || echo "")
if [ -z "$PNPM_VERSION" ]; then
    echo -e "检查 pnpm... ${RED}✗ 未安装${NC} (推荐)"
    echo -e "  ${YELLOW}启用: corepack enable${NC}"
    ((ERRORS++))
else
    echo -e "检查 pnpm... ${GREEN}✓${NC} $PNPM_VERSION"
fi

# 2. Python / uv
echo ""
echo "【后端工具链】"
UV_VERSION=$(uv --version 2>/dev/null || echo "")
if [ -z "$UV_VERSION" ]; then
    echo -e "检查 uv... ${RED}✗ 未安装${NC}"
    ((ERRORS++))
else
    echo -e "检查 uv... ${GREEN}✓${NC} $UV_VERSION"
fi

if [ -n "$UV_VERSION" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT_DIR/.local/uv-cache}"
    export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$ROOT_DIR/.local/uv-python}"
    PYTHON_VERSION=$(uv run --project "$ROOT_DIR/apps/api" --extra dev --frozen python --version 2>&1 || echo "")
else
    PYTHON_VERSION=""
fi
check_version "项目 Python" "uv run python --version" "3.11" "$PYTHON_VERSION"

# 3. Docker
echo ""
echo "【基础设施】"
DOCKER_VERSION=$(docker --version 2>/dev/null | grep -oP '[\d\.]+' | head -1 || echo "")
check_version "Docker" "docker --version" "24" "$DOCKER_VERSION"

DOCKER_COMPOSE_VERSION=$(docker compose version 2>/dev/null | grep -oP '[\d\.]+' | head -1 || echo "")
if [ -z "$DOCKER_COMPOSE_VERSION" ]; then
    echo -e "检查 Docker Compose... ${RED}✗ 未安装${NC}"
    ((ERRORS++))
else
    echo -e "检查 Docker Compose... ${GREEN}✓${NC} $DOCKER_COMPOSE_VERSION"
fi

# 4. Git
echo ""
echo "【版本控制】"
GIT_VERSION=$(git --version 2>/dev/null | grep -oP '[\d\.]+' | head -1 || echo "")
check_version "Git" "git --version" "2.40" "$GIT_VERSION"

# 总结
echo ""
echo "=================================="
echo "检查总结"
echo "=================================="

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有工具版本符合要求${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ 有 $WARNINGS 个警告，请检查上述信息${NC}"
    exit 0
else
    echo -e "${RED}✗ 发现 $ERRORS 个错误，请先安装缺失工具${NC}"
    echo ""
    echo "安装建议："
    echo "  - Node.js: https://nodejs.org/"
    echo "  - uv: https://docs.astral.sh/uv/getting-started/installation/"
    echo "  - Docker: https://docs.docker.com/get-docker/"
    echo "  - Git: https://git-scm.com/downloads/"
    exit 1
fi
