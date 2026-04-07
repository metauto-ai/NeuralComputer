#!/usr/bin/env python3
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class CommandBuilder(ABC):
    """Compatibility interface for command builders.

    Internal call sites use concrete builder methods directly. This interface is
    kept to avoid breaking external imports until a removal window is defined.
    """

    @abstractmethod
    def build_command(self, **options) -> List[str]:
        """Build a command from keyword options."""

    @abstractmethod
    def validate_options(self, **options) -> bool:
        """Validate keyword options for command construction."""
