function createObstacles(levelCfg, worldSize = 100, seed = 7) {
  let s = seed + levelCfg.level * 101;
  const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  return Array.from({ length: levelCfg.obstacles }, (_, i) => ({
    id: `obs-${i + 1}`,
    x: Math.round(rnd() * worldSize * 100) / 100,
    y: Math.round(rnd() * worldSize * 100) / 100,
    z: Math.round(rnd() * 20 * 100) / 100,
    r: levelCfg.radius,
  }));
}

function findCollisions(agents, obstacles) {
  const hit = [];
  for (const a of agents) {
    for (const o of obstacles) {
      const dx = a.x - o.x, dy = a.y - o.y, dz = a.z - o.z;
      if (Math.sqrt(dx * dx + dy * dy + dz * dz) < o.r) {
        hit.push(a.id);
        break;
      }
    }
  }
  return hit;
}

module.exports = { createObstacles, findCollisions };