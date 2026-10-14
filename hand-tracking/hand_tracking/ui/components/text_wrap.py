"""Keep explanatory labels wrapped to their container's current width."""


class WrapToWidth:
    def __init__(self, owner, labels, appearance, *, inset=36):
        self.owner = owner
        self.labels = tuple(labels)
        self.appearance = appearance
        self.inset = inset
        owner.bind("<Configure>", self.refresh, add="+")

    def refresh(self, _event=None):
        if self.owner.winfo_width() <= 1:
            return
        width = max(1, self.owner.winfo_width() - self.appearance.pixels(self.inset))
        for label in self.labels:
            if int(label.cget("wraplength")) != width:
                label.configure(wraplength=width)
