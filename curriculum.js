const LEVELS = [
  { level: 1, obstacles: 3, radius: 3.0, wind: 0.0 },
  { level: 2, obstacles: 6, radius: 3.5, wind: 0.2 },
  { level: 3, obstacles: 9, radius: 4.0, wind: 0.4 },
  { level: 4, obstacles: 12, radius: 4.5, wind: 0.6 },
  { level: 5, obstacles: 15, radius: 5.0, wind: 0.8 },
];

function difficultyScore(cfg) {
  return cfg.obstacles * cfg.radius * cfg.radius * (1 + cfg.wind);
}

// Returns a list of problems (empty list = data is valid).
function validateCurriculum(levels) {
  const problems = [];
  levels.forEach((l, i) => {
    for (const k of ['level', 'obstacles', 'radius', 'wind']) {
      if (typeof l[k] !== 'number' || Number.isNaN(l[k])) problems.push(`level ${i + 1}: ${k} missing or not a number`);
    }
    if (l.obstacles < 0 || l.radius <= 0 || l.wind < 0) problems.push(`level ${i + 1}: negative or zero value`);
    if (l.level !== i + 1) problems.push(`level ${i + 1}: levels must be numbered 1..N in order`);
    if (i > 0 && difficultyScore(l) <= difficultyScore(levels[i - 1])) {
      problems.push(`level ${l.level}: difficulty does not increase over level ${l.level - 1}`);
    }
  });
  return problems;
}

// Which level applies at a given step (the last level keeps going).
function levelForStep(step, stepsPerLevel, levels = LEVELS) {
  const idx = Math.min(levels.length - 1, Math.floor(Math.max(0, step - 1) / stepsPerLevel));
  return levels[idx];
}

module.exports = { LEVELS, difficultyScore, validateCurriculum, levelForStep };