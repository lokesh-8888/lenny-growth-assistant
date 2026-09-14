"""
Application middleware package.
"""

from app.middleware.trace import TraceMiddleware

__all__ = ["TraceMiddleware"]
