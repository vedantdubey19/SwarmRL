# Saju Telemetry Bundle Archive

## Day 23 objective

Package a completed and validated telemetry bundle into a portable ZIP
archive.

The archive contains the original metrics log, event log, combined report,
health-check result, and bundle manifest.

## Archive contents

```text
metrics.jsonl
events.jsonl
report.json
health.json
manifest.json
archive.json
```

`archive.json` describes the archive itself and lists its required
artifacts.

## Archive metadata

```json
{
  "schema_version": 1,
  "created_at": "2026-10-09T09:00:00+00:00",
  "artifacts": [
    "metrics.jsonl",
    "events.jsonl",
    "report.json",
    "health.json",
    "manifest.json"
  ]
}
```

## Public API

```python
create_telemetry_archive(...)
verify_telemetry_archive(...)
```

The `TelemetryArchive` value object provides:

```python
archive.to_dict()
archive.to_json()
```

## Validation

Archive creation rejects:

- Missing input files.
- Invalid input suffixes.
- Invalid archive output suffix.
- Naive timestamps.
- Clocks that do not return `datetime` values.

## Verification

Archive verification checks that:

- The archive is a valid ZIP file.
- All required entries are present.
- `archive.json` is valid JSON.
- The archive schema version is supported.
- JSON artifacts contain JSON objects.
- JSONL artifacts contain valid JSON lines.

Verification returns `True` for a valid archive and raises
`TelemetryArchiveError` for an invalid archive.

## Responsibility boundary

This module does not:

- Generate telemetry.
- Modify source artifacts.
- Repair invalid archives.
- Replace health checks or manifests.
- Run simulation or training.

It packages and verifies completed telemetry bundles.