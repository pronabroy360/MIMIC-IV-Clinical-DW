"""Prompt templates for optional external LLM integration."""

SYSTEM_PROMPT = """You generate privacy-preserving aggregate SQL for MIMIC-IV analytics.
Use only the provided schema context. Return read-only DuckDB SQL only. Do not
select raw identifiers, do not use SELECT *, do not query Bronze tables, and do
not produce patient-level rows."""

USER_PROMPT_TEMPLATE = """Schema context:
{schema_context}

Question:
{question}

Return a single aggregate SQL query with a LIMIT clause."""
