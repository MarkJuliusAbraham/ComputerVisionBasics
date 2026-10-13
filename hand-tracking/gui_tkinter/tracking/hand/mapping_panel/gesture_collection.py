"""Staged gesture names, membership, and selection without Tk dependencies."""

from dataclasses import replace


class GestureCollectionDraft:
    def __init__(self, definitions):
        self.original = tuple(definitions)
        self.definitions = self.original
        self.selected_id = self.definitions[0].id if self.definitions else None

    @property
    def is_dirty(self):
        return self.definitions != self.original

    @property
    def selected(self):
        return next((item for item in self.definitions if item.id == self.selected_id), None)

    def select(self, gesture_id):
        if not any(item.id == gesture_id for item in self.definitions):
            raise ValueError("This gesture is no longer in the active profile")
        self.selected_id = gesture_id

    def discard(self):
        self.definitions = self.original
        if not any(item.id == self.selected_id for item in self.definitions):
            self.selected_id = self.definitions[0].id if self.definitions else None

    def rename(self, gesture_id, name):
        self.select(gesture_id)
        self.definitions = tuple(
            replace(item, name=name.strip()) if item.id == gesture_id else item
            for item in self.definitions
        )

    def add(self, definition):
        if any(item.id == definition.id for item in self.definitions):
            raise ValueError("Gesture IDs must be unique")
        self.definitions += (definition,)
        self.selected_id = definition.id

    def delete(self, gesture_id):
        self.select(gesture_id)
        if len(self.definitions) <= 1:
            raise ValueError("A profile must contain at least one gesture")
        index = next(i for i, item in enumerate(self.definitions) if item.id == gesture_id)
        self.definitions = tuple(item for item in self.definitions if item.id != gesture_id)
        self.selected_id = self.definitions[min(index, len(self.definitions) - 1)].id
