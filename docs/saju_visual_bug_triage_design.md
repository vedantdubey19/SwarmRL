# Saju Visual Bug Triage

## Day 29 objective

Classify and track visual bugs found during full integration testing.

## Scope

This module records and exports triage information for visual bugs. It
does not render visuals, modify the environment, or start training.

## Public API

```python
triage_visual_bug(...)
update_visual_bug_status(...)
export_visual_bug_triage(...)
```

## Bug fields

Each triage record contains:

- Bug ID.
- Title.
- Description.
- Severity.
- Status.
- Assignee.
- Timezone-aware creation timestamp.

## Severity levels

```text
low
medium
high
critical
```

## Status values

```text
open
in_progress
resolved
closed
```

## Validation

The module rejects:

- Empty bug IDs, titles, or descriptions.
- Invalid severity values.
- Invalid status values.
- Naive timestamps.
- Clocks that do not return `datetime` values.

## Responsibility boundary

This module does not:

- Generate telemetry.
- Modify source artifacts.
- Start training.
- Render visuals.
- Automatically resolve bugs.

It records, updates, and exports visual bug triage information.