"""Exceptions raised by the CLEM-Reg pipeline.

Every pipeline error subclasses `ClemregError`, which subclasses
`Exception` directly and never `RuntimeError`. superqt's generator
workers (used by the Run Registration widget) treat a `RuntimeError`
as "the worker object was deleted" and swallow it without emitting
`errored` or `finished`, which left Register silently hung (#53).

See docs/design/package-split.md (decision D3). This module moves to
the `clemreg` core package in phase 2 of the split.
"""


class ClemregError(Exception):
    """Base class for errors raised by the CLEM-Reg pipeline."""
