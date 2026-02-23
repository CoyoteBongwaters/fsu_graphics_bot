# PSD Template Contract (Automation-Ready)

This repo generates a `render_plan` from event JSON. Photoshop automation will execute that plan.
To keep automation deterministic, PSD templates must follow this naming contract.

## Layer naming

### Text layers
- Prefix: `TEXT_`
- Examples:
  - `TEXT_WINNER`
  - `TEXT_LOSER`
  - `TEXT_WINNER_SCORE`
  - `TEXT_LOSER_SCORE`

Text layers must be actual Photoshop text layers.

### Smart object layers (replaceable images)
- Examples:
  - `LOGO_PRIMARY`
  - `LOGO_SECONDARY`
  - `HEADSHOT`
  - `BACKGROUND`

These layers must be Smart Objects (so the automation can replace contents while preserving transforms).

### Toggle groups / layers
- Used to show/hide optional elements based on data.
- Examples:
  - `HAS_HEADSHOT`

These should be groups (preferred) containing the optional sub-layout.

## Template map bindings

`template_map.json` defines `render_spec`:

- `text`: layer_name -> binding_path
- `images`: layer_name -> binding_path
- `toggles`: group_or_layer_name -> binding_path

Binding paths reference fields in the serialized Event:
- `meta.winner`
- `meta.winner_score`
- `assets.logo_primary`
- `assets.logo_secondary`
- `assets.headshot`
- `assets.background`

Toggle convention:
- If binding resolves to None/empty/[] -> toggle false
- Otherwise -> toggle true

## Required behavior

- A template must not depend on a field that is frequently missing unless it has a toggle fallback.
- If `logo_secondary` is missing, templates should still render correctly (single-team layout or hide secondary logo group).
- If `players` is empty, `HAS_HEADSHOT` should hide the headshot group.

## Versioning

Event JSON includes:
- `schema_version`

If the contract changes, bump schema_version and update template specs accordingly.