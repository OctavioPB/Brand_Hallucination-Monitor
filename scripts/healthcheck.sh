#!/usr/bin/env bash
# healthcheck.sh — verify all hallucin8 services are live
# Usage: bash scripts/healthcheck.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"

    if eval "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC}  $name"
        ((PASS++)) || true
    else
        echo -e "  ${RED}✗${NC}  $name"
        ((FAIL++)) || true
    fi
}

echo ""
echo "hallucin8 — service health check"
echo "================================="

# PostgreSQL
check "PostgreSQL 16" \
    "docker exec hallucin8-postgres pg_isready -U hallucin8 -d hallucin8 -q"

# Redis
check "Redis 7" \
    "docker exec hallucin8-redis redis-cli ping | grep -q PONG"

# Qdrant
check "Qdrant vector DB" \
    "curl -sf http://localhost:6333/healthz"

# Neo4j
check "Neo4j 5.x (HTTP)" \
    "curl -sf http://localhost:7474"

# Neo4j Bolt
check "Neo4j 5.x (Bolt)" \
    "docker exec hallucin8-neo4j cypher-shell -u neo4j -p hallucin8pass 'RETURN 1' > /dev/null 2>&1"

# Redpanda
check "Redpanda broker" \
    "docker exec hallucin8-redpanda rpk cluster health 2>/dev/null | grep -q 'Healthy:.*true'"

# Redpanda Schema Registry
check "Redpanda schema registry" \
    "curl -sf http://localhost:8081/subjects"

# Redpanda Console
check "Redpanda console" \
    "curl -sf http://localhost:8080/api/cluster/overview"

# FastAPI (if running)
check "FastAPI /health (optional)" \
    "curl -sf http://localhost:8000/health" || true

echo ""
echo "================================="
echo -e "  Passed: ${GREEN}${PASS}${NC}   Failed: ${RED}${FAIL}${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${YELLOW}Some services are not ready. Run 'make up' and wait 30s, then retry.${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}All services healthy. Stack is ready.${NC}"
echo ""
