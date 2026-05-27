"""SQL safety checks for aggregate-only natural language querying."""

from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_ALLOWED_TABLES = {
    "gold_patient_summary",
    "gold_admission_summary",
    "gold_icu_stay_summary",
    "gold_first_24h_features",
    "gold_lab_features",
    "gold_vital_features",
    "gold_diagnosis_features",
}

BLOCKED_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "COPY",
    "EXPORT",
    "PRAGMA",
    "ATTACH",
    "DETACH",
}

RAW_ID_COLUMNS = {"subject_id", "hadm_id", "stay_id"}
AGGREGATE_RE = re.compile(r"\b(count|avg|sum|min|max|median|quantile|stddev|variance)\s*\(", re.I)


@dataclass(frozen=True)
class GuardrailResult:
    """Validated SQL or rejection reasons."""

    allowed: bool
    sql: str | None
    reasons: tuple[str, ...] = ()


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.M)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    return sql.strip()


def _referenced_tables(sql: str) -> set[str]:
    tables: set[str] = set()
    for match in re.finditer(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", sql, flags=re.I):
        tables.add(match.group(1).split(".")[-1].lower())
    return tables


def _select_clause(sql: str) -> str:
    match = re.search(r"\bselect\b(?P<select>.*?)\bfrom\b", sql, flags=re.I | re.S)
    return match.group("select") if match else ""


def _remove_aggregate_calls(select_clause: str) -> str:
    """Remove simple aggregate call contents before checking projected raw IDs."""
    result = select_clause
    previous = None
    while previous != result:
        previous = result
        result = re.sub(
            r"\b(count|avg|sum|min|max|median|quantile|stddev|variance)\s*\([^()]*\)",
            "",
            result,
            flags=re.I,
        )
    return result


def _has_limit(sql: str) -> bool:
    return bool(re.search(r"\blimit\s+\d+\b", sql, flags=re.I))


def _append_limit(sql: str, limit: int) -> str:
    cleaned = sql.strip().rstrip(";")
    return f"{cleaned}\nLIMIT {limit}"


def validate_aggregate_sql(
    sql: str,
    allowed_tables: set[str] | None = None,
    default_limit: int = 100,
) -> GuardrailResult:
    """Validate and lightly rewrite aggregate SQL for safe execution."""
    allowed_tables = allowed_tables or DEFAULT_ALLOWED_TABLES
    cleaned = _strip_comments(sql)
    upper = cleaned.upper()
    reasons: list[str] = []

    if not re.match(r"^\s*SELECT\b", cleaned, flags=re.I):
        reasons.append("Only SELECT statements are allowed")
    if ";" in cleaned.rstrip(";"):
        reasons.append("Multiple SQL statements are not allowed")
    for keyword in BLOCKED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            reasons.append(f"Blocked keyword: {keyword}")
    if re.search(r"\bSELECT\s+\*", cleaned, flags=re.I):
        reasons.append("SELECT * is not allowed")
    if re.search(r"\bbronze_", cleaned, flags=re.I):
        reasons.append("Bronze tables are not allowed")
    if not AGGREGATE_RE.search(cleaned):
        reasons.append("Query must use an aggregate function")

    tables = _referenced_tables(cleaned)
    if not tables:
        reasons.append("Query must reference an allowed Gold table")
    disallowed = tables - {table.lower() for table in allowed_tables}
    if disallowed:
        reasons.append(f"Disallowed table(s): {', '.join(sorted(disallowed))}")

    projected = _remove_aggregate_calls(_select_clause(cleaned)).lower()
    projected = re.sub(r"'[^']*'", "", projected)
    for raw_id in RAW_ID_COLUMNS:
        if re.search(rf"\b{raw_id}\b", projected):
            reasons.append(f"Raw identifier projection is not allowed: {raw_id}")

    if reasons:
        return GuardrailResult(False, None, tuple(dict.fromkeys(reasons)))

    safe_sql = cleaned.rstrip(";")
    if not _has_limit(safe_sql):
        safe_sql = _append_limit(safe_sql, default_limit)
    return GuardrailResult(True, safe_sql, ())
