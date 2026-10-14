"""Staged gesture names, membership, and selection without Tk dependencies."""

from dataclasses import replace

from hand_tracking.backend.gestures.gesture_config import find_definition

MISSING_GESTURE = "This gesture is no longer in the active profile"


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
        return find_definition(self.definitions, self.selected_id)

    def contains(self, gesture_id):
        return find_definition(self.definitions, gesture_id) is not None

    def select(self, gesture_id):
        if not self.contains(gesture_id):
            raise ValueError(MISSING_GESTURE)
        self.selected_id = gesture_id

    def discard(self):
        self.definitions = self.original
        if not self.contains(self.selected_id):
            self.selected_id = self.definitions[0].id if self.definitions else None

    def rename(self, gesture_id, name):
        self.select(gesture_id)
        self.definitions = tuple(
            replace(item, name=name.strip()) if item.id == gesture_id else item
            for item in self.definitions
        )

    def add(self, definition):
        if self.contains(definition.id):
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
