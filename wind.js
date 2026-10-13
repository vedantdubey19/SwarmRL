function windForce(step, strength) {
  const angle = step * 0.05;
  const gust = 1 + 0.5 * Math.sin(step * 0.3);
  return { dx: Math.cos(angle) * strength * gust, dy: Math.sin(angle) * strength * gust };
}

function applyWind(agents, step, strength) {
  if (!strength) return agents;
  const { dx, dy } = windForce(step, strength);
  return agents.map((a) => ({ ...a, x: a.x + dx, y: a.y + dy }));
}

module.exports = { windForce, applyWind };