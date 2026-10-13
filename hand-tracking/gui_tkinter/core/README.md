# UI responsibilities

The hub and each tracking workspace use `WindowShell` for notebook composition
and `WindowLifecycleController` for visibility and unsaved-change decisions.
Tracking-specific controls belong under `tracking/<module>/`.
Shared package initializers remain lightweight; import controls and services
from the modules that define them.

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
- Gesture pattern creation belongs to `gestures/GestureFactory`, which can be
  injected into gesture management.
- `LiveHandData` is the single report used for debugging status and settings
  previews, so those consumers derive their messages from the same data.

Settings Apply, mapping Save, and gesture-management Save remain separate
commit operations. Reusable widgets do not read or write configuration files.
