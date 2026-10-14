# UI responsibilities

The hub and each tracking workspace use `WindowShell` for notebook composition
and `WindowLifecycleController` for visibility and unsaved-change decisions.
Tracking-specific controls belong under `tracking/<module>/`.
Packages have no `__init__.py`; import controls and services from the
modules that define them.

`WindowContext` carries shared window dependencies. `ControlWindowContext`
extends it with the hub's required tracking registry. `PanelCollection` and
the panel protocols describe the shell's interfaces; `PanelSet` retains the
concrete main-panel type for its application owner. Callback signatures are
declared in `callbacks.py`, with scoped values declared by the settings manager.

## Shared behavior

- `ChangeNotifications` owns variable subscriptions. Use `suspended()` while
  loading a draft; nested loads remain silent. Subscriptions are removed when
  the owning widget is destroyed.
- `IdleRefresh` queues at most one refresh for a widget and cancels queued work
  on destruction. Use it for theme events and geometry-driven refreshes.
- `ModalDialog` owns fixed sizing, initial parent-relative placement, and modal
  grabs. It restores a containing dialog's grab after a nested dialog closes.
  Persistent tracking windows use `TrackingWindow` instead.
- `UnsavedChangesGuard` accepts a `PendingChanges` object. Notebook navigation,
  profile changes, and gesture management share its Save/Discard/Return rules.
- `ScaledLayout` records a widget's `pack`/`grid`/`configure` spacing once, in
  100%-scale pixels, and re-applies it after theme or UI-scale changes. Use it
  instead of writing the same padding again in a refresh method.
- `widget_tree.walk_widgets` visits Python-owned widgets; `root_service` keeps
  one style or binding provider per Tk interpreter.
- `win32` loads `user32` once with typed signatures and shared error checks for
  the overlay, title-bar, and fixed-window styling code.

## Reusable controls

`components/` contains controls independent of profile persistence:
`FieldSection` builds declarative settings fields, `CommitActions` owns
save/discard state, and `StatusMessage` reserves space for themed feedback.
Typography and spacing come from `ThemeMetrics`; semantic colors come from
the theme provider.

## Editing data

- `SettingsSession` groups the applied settings and raw form baseline. Widgets
  retain incomplete numeric text; validation happens when applying changes.
- `MappingSession` owns profile persistence and mapping drafts.
  `MappingCallbacks` supplies the view's actions as one dependency.
- `GestureCollectionDraft` stages names, membership, and selection. The gesture
  manager controller and context-menu actions use the same operations.
  `GestureManagerView` only renders the collection and forwards interactions.
- Gesture pattern creation belongs to `hand_tracking/gestures/GestureFactory`, which can be
  injected into gesture management.
- `LiveHandData` is the single report used for debugging status, settings
  previews, and the desktop overlay. `HandSummaryData` formats gesture and
  command text for both the widget view and the raster overlay.
- `ClickThroughOverlayWindow` owns transparent window creation and placement;
  `WindowsOverlayStyle` owns native input/focus behavior. `HandTrackingOverlay`
  owns its display lifecycle. The hand module combines debugger visibility
  and overlay activity before notifying the application; manual pause and
  tracking/model settings still take precedence.
- `HandOverlayRenderer` paints grayscale-antialiased text and themed bars into
  an RGBA image. Only background surfaces receive the opacity setting.
  Light-theme text has an opaque, theme-colored outline to retain contrast
  when the backdrop fades. The outline and glyph masks share the raster cache.
  `WindowsLayeredPresenter` packs premultiplied pixels for `UpdateLayeredWindow`
  and reuses its native bitmap/DC. No color key or whole-window alpha is used;
  dragging changes native placement without repainting the data.
- `OverlaySettings` groups style, background opacity, and desktop position in
  the application settings file. `OverlayOptionsDialog` previews its own draft
  and reuses commit/discard actions and the unsaved-changes guard. Repositioning
  temporarily allows drag input; finishing restores click-through behavior.
  Pretty and Simple share the same renderer, summary formatter, and deviation
  table formatting; the compact presentation removes card borders and spacing.

Settings Apply, mapping Save, and gesture-management Save remain separate
commit operations. Reusable widgets do not read or write configuration files.
