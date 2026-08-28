"""Standalone runtime for Manuscript Revision Closure."""

__version__ = "0.6.3"

from .assessor import AnalysisResult, RunOptions, analyze_manuscript

__all__ = ["AnalysisResult", "RunOptions", "analyze_manuscript"]
