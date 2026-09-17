# Saju Sensor Observation Interface

## Owner

Saju

## Purpose

This module combines a drone's own state, visible objects, and explored
area into outputs that can be used by reinforcement-learning training,
WebSocket streaming, and frontend visualization.

## Observation components

Each observation contains:

- Agent ID
- Position `[x, y, z]`
- Heading in radians
- Visible object detections
- Explored-map fraction

## Reinforcement-learning vector

The vector contains:

### Own state

1. Normalized x position.
2. Normalized y position.
3. Normalized z position.
4. Sine of heading.
5. Cosine of heading.
6. Explored-map fraction.

### Sensor state

For each visible object:

1. Object-type encoding.
2. Normalized distance.
3. Normalized angle.

The object portion is zero-padded to the configured maximum number of
objects.

With the default configuration:

```text
6 own-state values + (8 objects × 3 values) = 30 values
```

## JSON-friendly output

The `to_dict()` method returns:

- Agent ID.
- Position as x, y, and z fields.
- Heading.
- Explored fraction.
- Detection list.
- Visible target count.
- Visible obstacle count.
- Visible drone count.

The returned dictionary contains only JSON-compatible values and can be
passed to the WebSocket layer.

## Integration contract

Humera should confirm:

- Position coordinate convention.
- Position normalization limits.
- Heading convention.
- Final observation-space shape.

Arya can use `to_dict()` for streaming.

Venkatesh can use `to_vector()` for RL observations.

Dhruv can use the detection list and visible-object counts for rendering.