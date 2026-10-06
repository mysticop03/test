"""
core/batch_orchestrator.py
Re-exports ParallelRunner as BatchOrchestrator for seamless backward compatibility.
See core/parallel_runner.py for the full implementation.
"""
from core.parallel_runner import ParallelRunner, BatchOrchestrator

__all__ = ["ParallelRunner", "BatchOrchestrator"]
