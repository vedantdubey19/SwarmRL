# Saju Sensor Design

## Owner

Saju

## Purpose

Detect objects inside each drone's sensor range and field of view.

## Initial configuration

- Sensor range: 20 simulation units
- Field of view: 90 degrees
- Maximum detected objects: 8
- Supported objects: drones, obstacles, and targets
- Position format: `[x, y, z]`
- Heading: radians

## Detection output

Each detection contains:

- Object ID
- Object type
- Distance
- Relative angle

## RL output

Each visible object uses three values:

1. Encoded object type.
2. Normalized distance.
3. Normalized angle.

The result is zero-padded to a fixed size.