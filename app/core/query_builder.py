"""Safe SQL query building helpers.

Provides functions that validate column names against whitelists
before constructing dynamic SQL, preventing injection via f-strings.
"""

# Allowed columns for dynamic UPDATE SET clauses, per table.
_ALLOWED_UPDATE_COLUMNS: dict[str, set[str]] = {
    "error_alerts": {
        "status", "acknowledged_by", "acknowledged_at", "resolved_by", "resolved_at",
    },
    "llm_providers": {
        "name", "model_id", "api_key_encrypted", "base_url", "is_default", "is_active", "updated_at",
    },
    "incidents": {
        "status", "updated_at", "mitigated_at", "resolved_at", "resolution_summary",
    },
}

# Allowed columns for dynamic WHERE clauses, per table.
_ALLOWED_WHERE_COLUMNS: dict[str, set[str]] = {
    "impact_findings": {
        "analysis_id", "org_id", "severity", "finding_type",
    },
    "business_rules": {
        "org_id", "repo_name", "rule_type", "is_active",
    },
}


def build_set_clause(table: str, parts: list[str]) -> str:
    """Build a safe SET clause from a list of 'column = :param' strings.

    Validates that each column name is in the allowed list for the table.
    Raises ValueError if an unknown column is used.
    """
    allowed = _ALLOWED_UPDATE_COLUMNS.get(table)
    if allowed is None:
        raise ValueError(f"Tabela '{table}' nao tem whitelist de colunas para UPDATE")

    for part in parts:
        col_name = part.split("=")[0].strip()
        # Allow SQL functions like now() as values
        if col_name not in allowed:
            raise ValueError(f"Coluna '{col_name}' nao permitida para UPDATE em '{table}'")

    return ", ".join(parts)


def build_where_clause(table: str, conditions: list[str]) -> str:
    """Build a safe WHERE clause from a list of 'column = :param' strings.

    Validates that each column name is in the allowed list for the table.
    Raises ValueError if an unknown column is used.
    """
    allowed = _ALLOWED_WHERE_COLUMNS.get(table)
    if allowed is None:
        raise ValueError(f"Tabela '{table}' nao tem whitelist de colunas para WHERE")

    for cond in conditions:
        col_name = cond.split("=")[0].split()[0].strip()
        if col_name not in allowed:
            raise ValueError(f"Coluna '{col_name}' nao permitida para WHERE em '{table}'")

    return " AND ".join(conditions)
