"""
AI module - Integración con Ollama y personalización de CVs.
"""

from .ollama_client import OllamaClient
from .cv_personalizer import CVPersonalizer

__all__ = ['OllamaClient', 'CVPersonalizer']
