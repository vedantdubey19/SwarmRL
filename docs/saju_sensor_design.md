# Saju Sensor Design

## Owner

Saju

## Purpose

The sensor module determines what each drone can detect during each
simulation step.

## Coordinate convention

- Position format: `[x, y, z]`
- Ground plane: x-z
- Altitude axis: y
- Heading unit: radians
- Heading 0 direction: positive x-axis

These conventions must be confirmed with the environment owner before
integration.

## Initial configuration

- Sensor type: cone of vision
- Sensor range: 20 simulation units
- Field of view: 90 degrees
- Maximum detected objects: 8
- Supported objects: drones, obstacles, and targets

## Detection output

Each detection contains:

- Object ID
- Object type
- Distance
- Relative angle

Detections are sorted from nearest to farthest.

## Validation rules

- Sensor range must be greater than zero.
- Field of view must be greater than zero and no greater than 360 degrees.
- Maximum detected objects must be greater than zero.
- Objects outside the sensor range are ignored.
- Objects outside the field of view are ignored.
- Invalid position shapes raise a `ValueError`.

## Reinforcement-learning output

Each visible object uses three values:

1. Encoded object type.
2. Normalized distance.
3. Normalized angle.

The vector is zero-padded to a fixed size:

```text
maximum objects × 3
```

With the default configuration:

```text
8 × 3 = 24 values
```

Normalized values are clipped to the interval `[0, 1]`.