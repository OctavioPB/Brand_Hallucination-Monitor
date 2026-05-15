"""Enable scalar quantization on all Qdrant collections.

Run once after initial collection creation to reduce storage ~4x with minimal
accuracy loss (scalar quantization uses int8 instead of float32).

Usage:
    python scripts/init_qdrant_quantization.py [--dry-run]

Requires:
    QDRANT_URL and optionally QDRANT_API_KEY in environment or .env.local.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any


def _build_client() -> Any:
    from qdrant_client import QdrantClient
    from apps.api.config import get_settings

    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=30,
    )


def enable_quantization(dry_run: bool = False) -> None:
    """Enable ScalarQuantization on all existing collections."""
    from qdrant_client.http.models import (
        OptimizersConfigDiff,
        QuantizationConfig,
        ScalarQuantization,
        ScalarQuantizationConfig,
        ScalarType,
    )

    client = _build_client()
    collections = client.get_collections().collections

    if not collections:
        print("No collections found — run init_qdrant_collections.py first.")
        sys.exit(0)

    for coll in collections:
        name = coll.name
        info = client.get_collection(name)
        current_quantization = info.config.quantization_config

        if current_quantization is not None:
            print(f"  [skip] {name} — quantization already configured")
            continue

        print(f"  {'[dry-run]' if dry_run else '[apply]'} {name} → ScalarQuantization(int8)")

        if dry_run:
            continue

        client.update_collection(
            collection_name=name,
            quantization_config=QuantizationConfig(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    quantile=0.99,  # preserve 99th-percentile range; avoids clipping outliers
                    always_ram=True,  # keep quantized vectors in RAM for fast queries
                )
            ),
            # Trigger re-optimization so existing segments get quantized
            optimizer_config=OptimizersConfigDiff(indexing_threshold=0),
        )
        print(f"    → done. Qdrant will re-optimize {name} in the background.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enable Qdrant scalar quantization")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be changed without applying",
    )
    args = parser.parse_args()

    print(f"Qdrant scalar quantization {'(dry run) ' if args.dry_run else ''}setup")
    print("=" * 60)

    enable_quantization(dry_run=args.dry_run)

    if not args.dry_run:
        print("\nQuantization enabled. Storage reduction takes effect as Qdrant")
        print("re-indexes segments in the background (~minutes for small collections).")
    else:
        print("\nDry run complete — no changes made.")


if __name__ == "__main__":
    main()
