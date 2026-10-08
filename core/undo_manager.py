"""
Undo / Redo (Geri / İleri Al) Yöneticisi
Komut Deseni (Command Pattern) tabanlı.
"""
from abc import ABC, abstractmethod
from typing import List, Callable, Optional
from core.logger import logger

class Command(ABC):
    description: str = "İşlem"

    @abstractmethod
    def execute(self) -> bool:
        pass

    @abstractmethod
    def undo(self) -> bool:
        pass

    def redo(self) -> bool:
        return self.execute()


class UndoManager:
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._on_change_callbacks: List[Callable[[], None]] = []

    def register_callback(self, cb: Callable[[], None]):
        self._on_change_callbacks.append(cb)

    def _notify(self):
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"UndoManager callback error: {e}")

    def execute_command(self, cmd: Command) -> bool:
        success = cmd.execute()
        if success:
            self._undo_stack.append(cmd)
            self._redo_stack.clear()
            if len(self._undo_stack) > self.max_history:
                self._undo_stack.pop(0)
            self._notify()
        return success

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        cmd = self._undo_stack.pop()
        try:
            success = cmd.undo()
            if success:
                self._redo_stack.append(cmd)
                self._notify()
                return True
            else:
                logger.warning(f"Undo failed for command: {cmd.description}")
                return False
        except Exception as e:
            logger.error(f"Error during undo: {e}")
            return False

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        cmd = self._redo_stack.pop()
        try:
            success = cmd.redo()
            if success:
                self._undo_stack.append(cmd)
                self._notify()
                return True
            else:
                logger.warning(f"Redo failed for command: {cmd.description}")
                return False
        except Exception as e:
            logger.error(f"Error during redo: {e}")
            return False

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        return self._undo_stack[-1].description if self._undo_stack else None

    def get_redo_description(self) -> Optional[str]:
        return self._redo_stack[-1].description if self._redo_stack else None

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()
