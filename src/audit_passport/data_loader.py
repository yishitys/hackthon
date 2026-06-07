from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .models import DataSourceCard, Evidence, SchemaCard


DATA_DIR = Path("data/kaggle")


@dataclass
class LoadedTable:
    path: Path
    dataframe: pd.DataFrame
    source_card: DataSourceCard
    schema_card: SchemaCard


def list_kaggle_csvs(data_dir: Path = DATA_DIR) -> list[Path]:
    if not data_dir.exists():
        return []
    return sorted(data_dir.glob("*.csv"))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def infer_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    columns = [str(col) for col in df.columns]
    lowered = {col: col.lower() for col in columns}
    entity_terms = ("batch", "product", "part", "customer", "supplier", "facility", "plant", "shipment", "inspection", "id")
    unit_terms = ("unit", "uom", "measure")
    date_terms = ("date", "time", "created", "updated", "loaded")

    entity_columns = [
        col
        for col in columns
        if any(term in lowered[col] for term in entity_terms)
        and not any(term in lowered[col] for term in unit_terms)
        and lowered[col] not in {"record_id", "id"}
        and "date" not in lowered[col]
    ]
    numeric_columns = [
        str(col)
        for col in df.select_dtypes(include=["number"]).columns
        if df[col].notna().any()
    ]
    unit_columns = [col for col in columns if any(term in lowered[col] for term in unit_terms)]
    date_columns = [col for col in columns if any(term in lowered[col] for term in date_terms)]

    return {
        "entity_columns": entity_columns[:8],
        "numeric_columns": numeric_columns[:12],
        "unit_columns": unit_columns[:8],
        "date_columns": date_columns[:8],
    }


def infer_entities(columns: list[str]) -> list[str]:
    entities: list[str] = []
    mapping = {
        "batch": "Batch",
        "product": "Product",
        "supplier": "Supplier",
        "facility": "Facility",
        "shipment": "Shipment",
        "inspection": "Inspection",
        "measurement": "Measurement",
    }
    for col in columns:
        lowered = col.lower()
        for needle, entity in mapping.items():
            if needle in lowered and entity not in entities:
                entities.append(entity)
    return entities or ["Record"]


def infer_grain(schema: dict[str, list[str]]) -> str:
    if schema["entity_columns"]:
        return "one row per " + " / ".join(schema["entity_columns"][:2])
    return "one row per source record"


def quality_summary(df: pd.DataFrame) -> dict[str, Any]:
    missing = {
        str(col): round(float(rate), 4)
        for col, rate in (df.isna().mean()).items()
        if float(rate) > 0
    }
    duplicate_rows = int(df.duplicated().sum())
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_rows": duplicate_rows,
        "missing_rate": dict(sorted(missing.items(), key=lambda item: item[1], reverse=True)[:10]),
    }


def load_kaggle_tables(data_dir: Path = DATA_DIR) -> list[LoadedTable]:
    tables: list[LoadedTable] = []
    for csv_path in list_kaggle_csvs(data_dir):
        df = pd.read_csv(csv_path)
        schema = infer_columns(df)
        source_id = csv_path.stem
        source_card = DataSourceCard(
            source_id=source_id,
            uri=str(csv_path).replace("\\", "/"),
            content_hash=file_hash(csv_path),
            row_count=int(len(df)),
            columns=[str(col) for col in df.columns],
            grain=infer_grain(schema),
            quality_summary=quality_summary(df),
        )
        schema_card = SchemaCard(
            source_id=source_id,
            entity_columns=schema["entity_columns"],
            numeric_columns=schema["numeric_columns"],
            unit_columns=schema["unit_columns"],
            date_columns=schema["date_columns"],
            inferred_entities=infer_entities([str(col) for col in df.columns]),
        )
        tables.append(LoadedTable(csv_path, df, source_card, schema_card))
    return tables


def value_preview(value: Any, max_length: int = 80) -> str:
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length] + ("..." if len(text) > max_length else "")


def evidence_for_rows(
    table: LoadedTable,
    rows: list[int],
    field_name: str,
    explanation: str,
    conflicting: str = "",
) -> list[Evidence]:
    evidence: list[Evidence] = []
    for row_index in rows[:4]:
        value = ""
        if 0 <= row_index < len(table.dataframe) and field_name in table.dataframe.columns:
            value = value_preview(table.dataframe.iloc[row_index][field_name])
        evidence.append(
            Evidence(
                source_file=table.path.name,
                row_number=str(row_index + 2),
                field_name=field_name,
                observed_value=value,
                expected_or_conflicting_value=conflicting,
                explanation=explanation,
            )
        )
    return evidence
