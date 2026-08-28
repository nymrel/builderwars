"""Public competition primitives for AgentWars."""

from .matrix import (
    REPORT_SCHEMA_VERSION,
    SCHEMA_VERSION,
    CompetitionConfigError,
    classify_pair,
    load_config,
    render_report,
    run_competition,
    validate_config,
    write_report,
)

__all__ = [
    "REPORT_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "CompetitionConfigError",
    "classify_pair",
    "load_config",
    "render_report",
    "run_competition",
    "validate_config",
    "write_report",
]
