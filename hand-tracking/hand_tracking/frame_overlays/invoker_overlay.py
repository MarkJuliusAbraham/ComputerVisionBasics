import cv2
import time
from pathlib import Path


class InvokerOverlay:
    def __init__(self):

        self.spell_stack = []
        self.images = {}

        self.current_image = None
        self.image_expiry = 0

        self.spell_book = {
            1: "",
            8: "Cold_Snap_icon.webp",           # 2 * 2 * 2
            12: "Ghost_Walk_icon.webp",         # 2 * 2 * 3
            20: "Ice_Wall_icon.webp",           # 2 * 2 * 5
            18: "Tornado_icon.webp",            # 2 * 3 * 3
            30: "Deafening_Blast_icon.webp",    # 2 * 3 * 5
            50: "Forge_Spirit_icon.webp",       # 2 * 5 * 5
            27: "emp.webp",                     # 3 * 3 * 3
            45: "Alacrity_icon.webp",           # 3 * 3 * 5
            75: "Chaos_Meteor_icon.webp",       # 3 * 5 * 5
            125: "Sun_Strike_icon.webp",        # 5 * 5 * 5
        }

        self.load_images()

    def load_images(self):
        image_dir = Path(__file__).parent / "images" / "invoker_spells"

        for file in image_dir.iterdir():
            if not file.is_file():
                continue

            image = cv2.imread(str(file))

            if image is not None:
                self.images[file.stem] = image

    def reset(self):
        """Forget queued elements and hide any displayed spell."""
        self.spell_stack.clear()
        self.current_image = None
        self.image_expiry = 0

    def addCommand(self, command):

        if command == 'q' or command == 'w' or command == 'e':
            self.spell_stack.append(command)

        if len(self.spell_stack) > 3:
            self.spell_stack.pop(0)

    def pollResult(self):
        # Do calculation
        if len(self.spell_stack) != 3:
            return ""

        product = 1
        print(self.spell_stack)

        for i in self.spell_stack:
            if i == 'q':
                product *= 2
            if i == 'w':
                product *= 3
            if i == 'e':
                product *= 5

        result = self.spell_book[product]
        print(result)

        # Load the spell image
        image = self.images.get(Path(result).stem)

        if image is not None:
            self.current_image = cv2.resize(image, (200, 200))
            self.image_expiry = time.time() + 1.0

        return result

    def handleDisplay(self, frame):
        # Keep displaying the current image until it expires
        if self.current_image is not None:
            if time.time() < self.image_expiry:
                height, width = frame.shape[:2]

                x = width - 200
                y = height - 200

                frame[y:y + 200, x:x + 200] = self.current_image
            else:
                self.current_image = None

        return frame
