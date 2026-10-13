# Saju Telemetry Bundle Manifest

## Day 22 objective

Create a reproducible manifest for a completed telemetry bundle.

The manifest describes the metrics log, event log, combined report,
and health-check result.

## Artifact metadata

Each artifact stores:

- Source path.
- File size in bytes.
- SHA-256 checksum.

The checksum allows later verification that the artifact has not changed.

## Manifest schema

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-06T12:10:00+00:00",
  "artifacts": {
    "metrics": {
      "path": "metrics.jsonl",
      "size_bytes": 100,
      "sha256": "..."
    },
    "events": {
      "path": "events.jsonl",
      "size_bytes": 100,
      "sha256": "..."
    },
    "report": {
      "path": "report.json",
      "size_bytes": 100,
      "sha256": "..."
    },
    "health": {
      "path": "health.json",
      "size_bytes": 100,
      "sha256": "..."
    }
  },
  "counts": {
    "metrics_records": 2,
    "event_records": 3
  },
  "healthy": true
}
```

## Public API

```python
build_telemetry_manifest(...)
export_telemetry_manifest(...)
verify_telemetry_manifest(...)
```

The `TelemetryManifest` value object provides:

```python
manifest.to_dict()
manifest.to_json()
```

## Validation

Manifest construction rejects:

- Missing files.
- Invalid file suffixes.
- Invalid JSONL records.
- Invalid health JSON.
- Health results without a boolean `healthy` field.
- Naive timestamps.
- Clocks that do not return `datetime` values.

## Verification

Verification recalculates each artifact's size and SHA-256 checksum.

It returns `True` when all supplied files match the manifest and `False`
when an existing file has changed.

Missing or invalid files raise `TelemetryManifestError`.

## Responsibility boundary

This module does not:

- Generate telemetry.
- Modify telemetry artifacts.
- Repair changed files.
- Replace health checks.
- Run simulation or training.

It records and verifies artifact identity.