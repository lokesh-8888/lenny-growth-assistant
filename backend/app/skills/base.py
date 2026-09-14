"""
BaseSkill interface for specialized generation skills (Ship 30, Markdown, HTML artifacts).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas import StructureValidation


class BaseSkill(ABC):
    """
    Abstract Base Class defining the protocol for generation skills.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the skill."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief summary of the skill's purpose."""
        pass

    @abstractmethod
    async def generate(
        self,
        context: str,
        topic: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Executes generation over provided grounded context.
        Returns dictionary containing:
        - title: str
        - content: str
        - word_count: int
        - validation: StructureValidation
        - citations: List[Dict[str, Any]]
        - served_by: str
        """
        pass

    @abstractmethod
    def validate(self, content: str) -> StructureValidation:
        """
        Programmatically evaluates structural constraints and word counts.
        """
        pass
