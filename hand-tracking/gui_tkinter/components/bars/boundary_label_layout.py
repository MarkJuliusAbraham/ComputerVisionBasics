"""Pack nearby boundary labels into reserved lanes without overlapping text."""


class BoundaryLabelLayout:
    def place(self, markers, widths, left, right, gap, lanes=3):
        groups = [[] for _ in range(lanes)]
        positions = {}
        levels = {}
        for index in range(len(markers)):
            candidates = []
            for level, group in enumerate(groups):
                indices = [*group, index]
                required = sum(widths[item] for item in indices) + gap * (len(indices) - 1)
                if required > right - left:
                    continue
                packed = self._pack(indices, markers, widths, left, right, gap)
                cost = sum((packed[item] - markers[item]) ** 2 for item in indices)
                candidates.append((cost + level * gap * gap, level, packed))
            if candidates:
                _cost, level, packed = min(candidates, key=lambda candidate: candidate[:2])
                groups[level].append(index)
                positions.update(packed)
            else:
                # An extremely narrow viewport cannot fit all text in three lanes.
                level = min(range(lanes), key=lambda lane: len(groups[lane]))
                groups[level].append(index)
                positions[index] = min(max(markers[index], left + widths[index] / 2),
                                       right - widths[index] / 2)
            levels[index] = level
        return [(positions[index], levels[index]) for index in range(len(markers))]

    @staticmethod
    def _pack(indices, markers, widths, left, right, gap):
        positions = {}
        edge = left
        for index in indices:
            positions[index] = max(markers[index], edge + widths[index] / 2)
            edge = positions[index] + widths[index] / 2 + gap
        edge = right
        for index in reversed(indices):
            positions[index] = min(positions[index], edge - widths[index] / 2)
            edge = positions[index] - widths[index] / 2 - gap
        return positions
