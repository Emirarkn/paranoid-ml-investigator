"""Paranoid ML Investigator — deterministic harness (Experimental Harness + Evidence layer).

The LLM agent (Claude Code, see CLAUDE.md) reasons and proposes; this package measures,
records and decides evidence status. Nothing the agent writes can change a status directly.
"""

__version__ = "0.1.0"

STATUSES = ("Suspected", "Verified", "Simulated", "Rejected", "Inconclusive")
