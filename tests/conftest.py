"""
Pytest configuration and fixtures.
"""

import pytest
from mlcf import ContextManager
from mlcf.core.config import Config


@pytest.fixture
def config():
    """Provide test configuration."""
    return Config(
        short_term_max_size=5,
        working_memory_max_size=20,
        debug=True
    )


@pytest.fixture
def context_manager(config):
    """Provide ContextManager instance for testing."""
    cm = ContextManager(config=config)
    yield cm
    # Cleanup
    cm.clear_short_term()
    cm.clear_working()


@pytest.fixture
def sample_documents():
    """Provide sample documents for testing."""
    return [
        {
            "content": "Python is a high-level programming language",
            "metadata": {"type": "fact", "topic": "programming"}
        },
        {
            "content": "User prefers functional programming style",
            "metadata": {"type": "preference", "category": "coding"}
        },
        {
            "content": "Currently working on ML project",
            "metadata": {"type": "task", "status": "active"}
        },
    ]