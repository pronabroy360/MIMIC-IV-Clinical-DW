"""FastAPI app for aggregate warehouse endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from src.api.routes_analytics import router as analytics_router
from src.api.routes_cohorts import router as cohorts_router
from src.api.routes_health import router as health_router
from src.core.config import WarehouseConfig, load_config
from src.core.db import connect
from src.llm.sql_guardrails import validate_aggregate_sql


def get_config() -> WarehouseConfig:
    """Load API config from environment or demo default."""
    return load_config(os.getenv("MIMIC_CONFIG_PATH", "configs/demo.duckdb.yaml"))


class QueryRequest(BaseModel):
    sql: str


query_router = APIRouter(tags=["query"])


@query_router.post("/query/aggregate")
def query_aggregate(request: QueryRequest) -> dict[str, object]:
    """Run a guarded aggregate SQL query."""
    config = get_config()
    guardrail = validate_aggregate_sql(
        request.sql,
        allowed_tables=set(config.llm.allowed_tables),
        default_limit=config.llm.default_limit,
    )
    if not guardrail.allowed or guardrail.sql is None:
        raise HTTPException(status_code=400, detail=list(guardrail.reasons))
    with connect(config) as con:
        rows = con.execute(guardrail.sql).fetchdf().to_dict(orient="records")
    return {"sql": guardrail.sql, "rows": rows}


app = FastAPI(
    title="MIMIC-IV Clinical Data Warehouse API",
    description="Aggregate-only local API for MIMIC-IV warehouse analytics.",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(cohorts_router)
app.include_router(query_router)
