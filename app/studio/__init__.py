"""Flagship studio layer for end-to-end showcase generation."""

from app.studio.flagship import (
    DEFAULT_STUDIO_SCENARIOS,
    FLAGSHIP_ONE_LINER,
    StudioShowcaseBuilder,
)
from app.studio.proposals import ProposalRegistry

__all__ = [
    "DEFAULT_STUDIO_SCENARIOS",
    "FLAGSHIP_ONE_LINER",
    "ProposalRegistry",
    "StudioShowcaseBuilder",
]
