"""
Core Interfaces for Axur Toolkit

This module defines the abstract base classes and interfaces that all
modules must implement to ensure plug-and-play compatibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from .axur_client import AxurClient


class UseCase(ABC):
    """
    Abstract Base Class for all Use Cases (Books in the Library).
    
    Every new module added to /use_cases/ must implement this class to be
    automatically discovered by the main application.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The display name for the menu (e.g., 'Risk Score v3.0')."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description for the menu (e.g., 'Calculate current security posture')."""
        pass
    
    @abstractmethod
    def run(self, client: AxurClient) -> None:
        """
        The entry point for the use case.
        
        Args:
            client: An authenticated AxurClient instance.
        """
        pass
