"""
Validation utilities for HAM.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        self.warnings.append(message)

    def merge(self, other: "ValidationResult"):
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def __bool__(self):
        return self.is_valid
