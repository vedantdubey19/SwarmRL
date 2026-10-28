import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FORBIDDEN_ROOT_FILES = [
    "server.js",
    "schema.js",
    "train.py",
    "reward.py",
    "mock-env-feed.js",
    "train_audit_trial1.py",
    "train_audit_trial2.py",
    "rllib_config.py",
    "bad-payload-test.js",
    "config.js",
    "curriculum.js",
    "grid-paint.js",
    "integration-test.js",
    "late-joiner-test.js",
    "latency-test.js",
    "obstacles.js",
    "render-check.js",
    "test-client.js",
    "test-curriculum.js",
    "test-grid-paint.js",
    "test-obstacles.js",
    "test-wind.js",
    "threejs-feed-client.js",
    "throughput-stress-test.js",
    "validate-50-agents.js",
    "validate-actor-observations.js",
    "verify-mappo-dataflow.js",
    "wind.js",
]


def test_no_forbidden_root_files_exist():
    found = []
    for fname in FORBIDDEN_ROOT_FILES:
        full_p = os.path.join(REPO_ROOT, fname)
        if os.path.exists(full_p):
            found.append(fname)
    assert not found, f"Forbidden legacy root files detected in repository: {found}"


def test_single_source_of_truth_env_and_reward_modules():
    # Only env.py in root or sensors allowed as env modules
    env_files = []
    reward_files = []

    for root, dirs, files in os.walk(REPO_ROOT):
        # Ignore .venv, node_modules, .git, qa
        if any(ignored in root for ignored in [".venv", "node_modules", ".git", "qa"]):
            continue
        for f in files:
            if f.endswith(".py"):
                if f in ("env.py", "drone_env.py", "environment.py"):
                    rel = os.path.relpath(os.path.join(root, f), REPO_ROOT)
                    env_files.append(rel)
                if f in ("reward.py", "rewards.py"):
                    rel = os.path.relpath(os.path.join(root, f), REPO_ROOT)
                    reward_files.append(rel)

    assert env_files == ["env.py"], f"Found competing env modules: {env_files}"
    assert reward_files == [os.path.join("sensors", "rewards.py")], f"Found competing reward modules: {reward_files}"


def test_no_hardcoded_endpoints_outside_documented_defaults():
    # Allowed files with documented default ws://localhost:8080 or ws://127.0.0.1:8080
    ALLOWED_FILES = {
        os.path.join("sensors", "ws_publisher.py"),
        os.path.join("server", "server.js"),
        os.path.join("frontend", "src", "utils", "url.js"),
        os.path.join("scripts", "run_live_sim.py"),
        os.path.join("scripts", "mock_feed.js"),
        ".env.example",
    }

    suspicious = []
    pattern = re.compile(r'(ws://|wss://|http://|https://)(localhost|127\.0\.0\.1)(:\d+)?')

    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip node_modules, .venv, .git, dist, runs, checkpoints, tests, docs, qa, reports
        if any(p in root for p in [".venv", "node_modules", ".git", "dist", "runs", "checkpoints", "tests", "docs", "qa", "reports"]):
            continue
        for f in files:
            if not f.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".yaml", ".json")):
                continue
            rel_p = os.path.relpath(os.path.join(root, f), REPO_ROOT)
            if rel_p in ALLOWED_FILES:
                continue

            with open(os.path.join(root, f), "r", encoding="utf-8", errors="ignore") as fp:
                for line_no, line in enumerate(fp, start=1):
                    match = pattern.search(line)
                    if match:
                        suspicious.append(f"{rel_p}:{line_no} -> {line.strip()}")

    assert not suspicious, f"Found hardcoded local host/port outside documented defaults:\n" + "\n".join(suspicious)
