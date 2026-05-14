#!/usr/bin/env bash
# create_topics.sh — provision all hallucin8 Kafka topics via rpk (Redpanda CLI)
# Usage: bash infra/kafka/create_topics.sh
#
# Runs against localhost:9092 by default.
# Override with: KAFKA_BOOTSTRAP=host:port bash create_topics.sh
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"
REPLICATION=1          # dev: single node; prod: change to 3
DEFAULT_RETENTION=604800000  # 7 days in ms

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

create_topic() {
    local name="$1"
    local partitions="${2:-4}"
    local retention="${3:-$DEFAULT_RETENTION}"

    if docker exec hallucin8-redpanda rpk topic describe "$name" &>/dev/null; then
        echo -e "  ${YELLOW}~${NC}  $name (already exists, skipping)"
    else
        docker exec hallucin8-redpanda rpk topic create "$name" \
            --brokers "$BOOTSTRAP" \
            --partitions "$partitions" \
            --replicas "$REPLICATION" \
            --topic-config "retention.ms=$retention" \
            --topic-config "cleanup.policy=delete"
        echo -e "  ${GREEN}✓${NC}  $name"
    fi
}

echo ""
echo "hallucin8 — Kafka topic provisioning"
echo "======================================"

# Core ingestion topics
create_topic "brand.mentions.raw"       4
create_topic "brand.mentions.enriched"  4   # intermediate: post-dedup + enrichment
create_topic "competitor.mentions.raw"  4

# Downstream processing
create_topic "embeddings.pending"       8   # higher partitions: parallel embedding workers

# Alerts output
create_topic "hallucination.alerts"     2

# Dead Letter Queue — long retention for replay
create_topic "mentions.dlq"            2   60480000000  # 700 days

echo ""
echo "======================================"
echo -e "  ${GREEN}Topics provisioned.${NC}"
echo "  Verify: docker exec hallucin8-redpanda rpk topic list"
echo ""
