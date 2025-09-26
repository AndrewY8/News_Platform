"""
Integration layer for connecting the aggregator with existing components.

This module provides integration classes and utilities for connecting
the news aggregator with the existing PlannerAgent and other system components.
"""

from .planner_aggregator import EnhancedPlannerAgent
from .realtime_processor import RealtimeProcessor

__all__ = [
    'EnhancedPlannerAgent',
    'RealtimeProcessor'
]
