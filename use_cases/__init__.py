"""
Use Case Registry (The Librarian)

This module acts as a dynamic registry that discovers and loads available Use Cases
from the subdirectories. This enables a 'plug-and-play' architecture where adding
a new folder with a compatible UseCase implementation automatically adds it to the application.
"""

import os
import pkgutil
import importlib
import inspect
import sys
from typing import List
from core.interfaces import UseCase

def get_available_use_cases() -> List[UseCase]:
    """
    Dynamically discover and instantiate all available Use Cases.
    
    scans the current directory for submodules, imports them, and looks for
    classes that inherit from core.interfaces.UseCase.
    
    Returns:
        List of instantiated UseCase objects.
    """
    use_cases = []
    package_dir = os.path.dirname(__file__)
    
    # Iterate over all subdirectories/modules in this package
    for _, module_name, is_pkg in pkgutil.iter_modules([package_dir]):
        if is_pkg:
            try:
                # Import the module
                full_module_name = f"use_cases.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # Inspect module for UseCase implementations
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) 
                        and issubclass(obj, UseCase) 
                        and obj is not UseCase):
                        
                        # Instantiate and add to list
                        use_cases.append(obj())
                        
            except Exception as e:
                print(f"⚠️  Failed to load use case '{module_name}': {e}")
    
    return use_cases
