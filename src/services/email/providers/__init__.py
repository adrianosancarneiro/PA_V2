"""Email provider normalization utilities.

This package contains provider-specific modules that fetch emails and
normalize them into a common :class:`NormalizedEmail` dataclass. These
utilities are used by higher level jobs to process emails uniformly
regardless of the source provider.
"""

from .model import NormalizedEmail

__all__ = ["NormalizedEmail"]
