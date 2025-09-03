"""
TrustGraph Confidence-Based Agent

This module implements a confidence-based agent architecture that provides
enhanced reliability and auditability compared to traditional ReAct agents.

The agent uses structured execution plans with confidence-based control flow,
ensuring high-quality outputs through systematic evaluation and retry mechanisms.
"""

__all__ = [
    "ConfidenceAgent",
    "ConfidenceMetrics", 
    "ExecutionStep",
    "ExecutionPlan",
    "StepResult"
]