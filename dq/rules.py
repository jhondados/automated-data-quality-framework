"""Core data quality rules engine."""
from dataclasses import dataclass
from typing import Optional
from google.cloud import bigquery
import pandas as pd

@dataclass
class QualityResult:
    rule_id: str
    table: str
    column: Optional[str]
    passed: bool
    score: float
    records_checked: int
    records_failed: int
    details: str

class DataQualityEngine:
    def __init__(self, project_id: str):
        self.bq = bigquery.Client(project=project_id)
        self.results = []

    def check_completeness(self, table: str, column: str, threshold: float = 0.99) -> QualityResult:
        sql = f"""SELECT COUNT(*) AS total, COUNTIF({column} IS NULL) AS nulls
               FROM `{table}`"""
        row = self.bq.query(sql).result().__iter__().__next__()
        total, nulls = row.total, row.nulls
        completeness = 1 - (nulls / total if total > 0 else 0)
        return QualityResult(rule_id=f"completeness_{column}", table=table, column=column,
            passed=completeness >= threshold, score=completeness,
            records_checked=total, records_failed=nulls,
            details=f"Completeness: {completeness:.4%} (threshold: {threshold:.4%})")

    def check_uniqueness(self, table: str, key_columns: list) -> QualityResult:
        cols = ", ".join(key_columns)
        sql = f"""SELECT COUNT(*) AS total,
               COUNT(*) - COUNT(DISTINCT CONCAT({", '|', ".join(key_columns)})) AS dupes
               FROM `{table}`"""
        row = next(self.bq.query(sql).result())
        score = 1 - (row.dupes / row.total if row.total > 0 else 0)
        return QualityResult(rule_id=f"uniqueness_{'_'.join(key_columns)}", table=table,
            column=cols, passed=score >= 0.9999, score=score,
            records_checked=row.total, records_failed=row.dupes,
            details=f"Uniqueness: {score:.6%}, Duplicates: {row.dupes:,}")
