#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

PARQUET_MAGIC = b"PAR1"


def _schema_fields(arrow_schema: pa.Schema) -> list[dict[str, Any]]:
    return [
        {
            "name": field.name,
            "type": str(field.type),
            "nullable": field.nullable,
        }
        for field in arrow_schema
    ]


def _column_statistics(column: Any) -> dict[str, Any] | None:
    stats = getattr(column, "statistics", None)
    if stats is None:
        return None

    return {
        "has_min_max": getattr(stats, "has_min_max", None),
        "min": getattr(stats, "min", None),
        "max": getattr(stats, "max", None),
        "null_count": getattr(stats, "null_count", None),
        "distinct_count": getattr(stats, "distinct_count", None),
        "num_values": getattr(stats, "num_values", None),
        "physical_type": getattr(stats, "physical_type", None),
    }


def _row_groups(metadata: Any) -> list[dict[str, Any]]:
    groups = []
    for index in range(metadata.num_row_groups):
        row_group = metadata.row_group(index)
        columns = []

        for column_index in range(row_group.num_columns):
            column = row_group.column(column_index)
            columns.append(
                {
                    "index": column_index,
                    "path_in_schema": column.path_in_schema,
                    "physical_type": column.physical_type,
                    "compression": str(column.compression),
                    "encodings": [str(encoding) for encoding in column.encodings],
                    "file_offset": getattr(column, "file_offset", None),
                    "dictionary_page_offset": getattr(column, "dictionary_page_offset", None),
                    "data_page_offset": getattr(column, "data_page_offset", None),
                    "total_compressed_size": getattr(column, "total_compressed_size", None),
                    "total_uncompressed_size": getattr(column, "total_uncompressed_size", None),
                    "num_values": getattr(column, "num_values", None),
                    "statistics": _column_statistics(column),
                }
            )

        groups.append(
            {
                "index": index,
                "num_rows": row_group.num_rows,
                "num_columns": row_group.num_columns,
                "total_byte_size": row_group.total_byte_size,
                "sorting_columns": getattr(row_group, "sorting_columns", None),
                "columns": columns,
            }
        )

    return groups


def _minimal_parquet_bytes(metadata_bytes: bytes) -> bytes:
    return PARQUET_MAGIC + metadata_bytes + len(metadata_bytes).to_bytes(4, "little") + PARQUET_MAGIC


def decode_parquet_metadata(metadata_bytes: bytes) -> dict[str, Any]:
    parquet_file = pq.ParquetFile(pa.BufferReader(_minimal_parquet_bytes(metadata_bytes)))
    metadata = parquet_file.metadata
    format_version = getattr(metadata, "format_version", None)

    return {
        "parquet_format_version": str(format_version) if format_version is not None else None,
        "created_by": metadata.created_by,
        "serialized_size": metadata.serialized_size,
        "num_rows": metadata.num_rows,
        "num_columns": metadata.num_columns,
        "num_row_groups": metadata.num_row_groups,
        "arrow_schema": str(parquet_file.schema_arrow),
        "parquet_schema": str(parquet_file.schema),
        "fields": _schema_fields(parquet_file.schema_arrow),
        "row_groups": _row_groups(metadata),
    }


def _read_input(args: argparse.Namespace) -> str:
    if args.base64:
        return args.base64.strip()

    if args.base64_env:
        value = os.environ.get(args.base64_env)
        if value is None:
            raise SystemExit(f"Environment variable '{args.base64_env}' is not set.")
        return value.strip()

    if args.base64_file:
        return Path(args.base64_file).read_text(encoding="utf-8").strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    raise SystemExit("Provide --base64, --base64-env, --base64-file, or pipe Base64 metadata on stdin.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Decode a Base64-encoded Parquet metadata block captured from Postman into structured JSON."
    )
    parser.add_argument("--base64", help="Base64-encoded Parquet metadata bytes")
    parser.add_argument("--base64-env", help="Environment variable name containing the Base64 metadata blob")
    parser.add_argument("--base64-file", help="Path to a file containing the Base64 metadata blob")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation level (default: 2)")
    args = parser.parse_args(argv)

    metadata_base64 = _read_input(args)
    metadata_bytes = base64.b64decode(metadata_base64, validate=True)
    decoded = decode_parquet_metadata(metadata_bytes)
    json.dump(decoded, sys.stdout, indent=args.indent, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
