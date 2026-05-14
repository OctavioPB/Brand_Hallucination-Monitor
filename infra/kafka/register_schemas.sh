#!/usr/bin/env bash
# register_schemas.sh — register Avro schemas with Redpanda Schema Registry
# Usage: bash infra/kafka/register_schemas.sh
#
# Requires: curl, jq
set -euo pipefail

SR_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"
SCHEMAS_DIR="$(cd "$(dirname "$0")/schemas" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'

register_schema() {
    local subject="$1"
    local avsc_file="$2"

    # Escape the schema JSON for embedding in the request body
    local schema_json
    schema_json=$(cat "$avsc_file" | tr -d '\n' | sed 's/"/\\"/g')

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST "$SR_URL/subjects/$subject/versions" \
        -H "Content-Type: application/vnd.schemaregistry.v1+json" \
        -d "{\"schema\": \"$schema_json\"}")

    local body http_code
    body=$(echo "$response" | head -n -1)
    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        local id
        id=$(echo "$body" | grep -o '"id":[0-9]*' | cut -d: -f2)
        echo -e "  ${GREEN}✓${NC}  $subject  (id=$id)"
    else
        echo -e "  ${RED}✗${NC}  $subject — HTTP $http_code: $body"
        return 1
    fi
}

echo ""
echo "hallucin8 — Schema Registry registration"
echo "=========================================="

register_schema "brand.mentions.raw-value"       "$SCHEMAS_DIR/brand_mention_event.avsc"
register_schema "brand.mentions.enriched-value"  "$SCHEMAS_DIR/brand_mention_event.avsc"
register_schema "competitor.mentions.raw-value"  "$SCHEMAS_DIR/competitor_mention_event.avsc"
register_schema "embeddings.pending-value"       "$SCHEMAS_DIR/brand_mention_event.avsc"
register_schema "mentions.dlq-value"             "$SCHEMAS_DIR/brand_mention_event.avsc"

echo ""
echo "=========================================="
echo -e "  ${GREEN}Schemas registered.${NC}"
echo "  Inspect: curl http://localhost:8081/subjects"
echo ""
