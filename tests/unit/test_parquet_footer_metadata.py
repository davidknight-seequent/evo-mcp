# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from evo_mcp.tools.admin_tools import (
    PARQUET_FOOTER_SIZE,
    _inspect_parquet_footer_bytes,
    _parquet_footer_metadata_length,
)


def test_inspect_parquet_footer_bytes_reads_metadata_without_full_file(tmp_path):
    table = pa.table({"sample_id": [1, 2], "grade": [1.5, 2.5]})
    parquet_path = tmp_path / "sample.parquet"
    pq.write_table(table, parquet_path)

    parquet_bytes = parquet_path.read_bytes()
    footer_bytes = parquet_bytes[-PARQUET_FOOTER_SIZE:]
    metadata_length = _parquet_footer_metadata_length(footer_bytes)
    metadata_and_footer = parquet_bytes[-(metadata_length + PARQUET_FOOTER_SIZE) :]

    result = _inspect_parquet_footer_bytes(
        "sample.parquet",
        metadata_and_footer,
        blob_size_bytes=len(parquet_bytes),
    )

    assert result["blob_name"] == "sample.parquet"
    assert result["size_bytes"] == len(parquet_bytes)
    assert result["num_rows"] == 2
    assert result["num_columns"] == 2
    assert result["num_row_groups"] == 1
    assert result["fields"] == [
        {"name": "sample_id", "type": "int64", "nullable": True},
        {"name": "grade", "type": "double", "nullable": True},
    ]
