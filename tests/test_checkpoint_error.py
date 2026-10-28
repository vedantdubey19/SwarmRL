import os
import tempfile
import pytest
from training.evaluate import load_actor_from_checkpoint, DecentralizedActor


def test_missing_checkpoint_raises_file_not_found():
    non_existent = "/path/to/definitely/non_existent_checkpoint_dir"
    with pytest.raises(FileNotFoundError, match="Checkpoint path does not exist"):
        load_actor_from_checkpoint(non_existent, allow_untrained=False)


def test_missing_checkpoint_allow_untrained_succeeds():
    non_existent = "/path/to/definitely/non_existent_checkpoint_dir"
    actor = load_actor_from_checkpoint(non_existent, allow_untrained=True)
    assert isinstance(actor, DecentralizedActor)


def test_empty_checkpoint_dir_raises_file_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(FileNotFoundError, match="No valid actor weights found"):
            load_actor_from_checkpoint(tmpdir, allow_untrained=False)


def test_empty_checkpoint_dir_allow_untrained_succeeds():
    with tempfile.TemporaryDirectory() as tmpdir:
        actor = load_actor_from_checkpoint(tmpdir, allow_untrained=True)
        assert isinstance(actor, DecentralizedActor)
