"""Traversal and per-interpreter services shared by theme and input helpers."""


def walk_widgets(parent, *, include_parent=True):
    """Yield Python-owned widgets depth-first, parents before children.

    ``children`` excludes Tk's private widgets (such as combobox popdowns),
    which cannot always be resolved back to Python objects.
    """
    if include_parent:
        yield parent
    for child in tuple(parent.children.values()):
        yield from walk_widgets(child)


def root_service(widget, attribute, factory):
    """Return the one ``factory(root)`` object stored on the widget's Tk root.

    Styles and bindings belong to the Tk interpreter, so windows and dialogs
    share a single provider instead of registering their own.
    """
    root = widget._root()
    service = getattr(root, attribute, None)
    if service is None:
        service = factory(root)
        setattr(root, attribute, service)
    return service
