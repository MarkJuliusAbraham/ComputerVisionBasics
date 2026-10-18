"""Temporary command-driven spell display, without a camera or keyboard."""

from itertools import combinations_with_replacement, permutations
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from hand_tracking.backend.frame_overlays.invoker_overlay import InvokerOverlay


class InvokerOverlayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 10.0
        self.overlay = InvokerOverlay(
            clock=lambda: self.now, image_dir=self.directory.name,
        )

    def save_icon(self, filename, color=123):
        cv2.imwrite(
            str(Path(self.directory.name) / filename),
            np.full((8, 8, 3), color, dtype=np.uint8),
        )

    def frame(self):
        return np.zeros((80, 100, 3), dtype=np.uint8)

    def test_all_spells_ignore_element_order(self):
        # Independent game rules, using counts of Quas, Wex, and Exort.
        rules = {
            (3, 0, 0): "Cold_Snap_icon.webp", (2, 1, 0): "Ghost_Walk_icon.webp",
            (2, 0, 1): "Ice_Wall_icon.webp", (1, 2, 0): "Tornado_icon.webp",
            (1, 1, 1): "Deafening_Blast_icon.webp", (1, 0, 2): "Forge_Spirit_icon.webp",
            (0, 3, 0): "emp.webp", (0, 2, 1): "Alacrity_icon.webp",
            (0, 1, 2): "Chaos_Meteor_icon.webp", (0, 0, 3): "Sun_Strike_icon.webp",
        }
        for index, filename in enumerate(rules.values(), start=1):
            self.save_icon(filename, index)
        for combination in combinations_with_replacement("qwe", 3):
            for elements in set(permutations(combination)):
                with self.subTest(elements=elements):
                    self.overlay.reset()
                    for key in elements:
                        self.overlay.on_command(key)
                    self.assertFalse(self.overlay.draw(self.frame()).any())
                    self.overlay.on_command("r")
                    counts = tuple(elements.count(key) for key in "qwe")
                    color = list(rules).index(counts) + 1
                    frame = self.overlay.draw(self.frame())
                    self.assertTrue((frame[:, 20:] == color).all())
                    self.assertFalse(frame[:, :20].any())

    def test_latest_three_survive_invoke_and_unrelated_keys(self):
        for key in "qwexqr":
            self.overlay.on_command(key)
        self.assertEqual(self.overlay.elements, ("w", "e", "q"))

    def test_expiry_reinvoke_and_reset(self):
        self.save_icon("Cold_Snap_icon.webp")
        for key in "qqqr":
            self.overlay.on_command(key)
        self.assertTrue(self.overlay.draw(self.frame()).any())
        self.now += 1.0
        self.assertFalse(self.overlay.draw(self.frame()).any())
        self.overlay.on_command("r")
        self.assertTrue(self.overlay.draw(self.frame()).any())
        self.overlay.reset()
        self.assertEqual(self.overlay.elements, ())
        self.assertFalse(self.overlay.draw(self.frame()).any())

    def test_incomplete_stack_and_missing_assets_are_harmless(self):
        for key in "rqrqr":
            self.overlay.on_command(key)
        self.assertFalse(self.overlay.draw(self.frame()).any())
        self.overlay.on_command("q")
        self.overlay.on_command("r")
        self.assertFalse(self.overlay.draw(self.frame()).any())
