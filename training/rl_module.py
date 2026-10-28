from typing import Any, Dict, Optional
import torch
import torch.nn as nn

from ray.rllib.core.rl_module.torch.torch_rl_module import TorchRLModule
from ray.rllib.core.rl_module.apis.value_function_api import ValueFunctionAPI
from ray.rllib.core.columns import Columns
from ray.rllib.models.torch.torch_distributions import TorchDiagGaussian


class SwarmCentralizedCriticRLModule(TorchRLModule, ValueFunctionAPI):
    """True MAPPO RLModule on RLlib New API Stack.

    Decentralized Actor consumes 81-dim local observation and outputs 4-D Gaussian action.
    Centralized Critic consumes 471-dim fixed-size global state and outputs scalar value.
    """

    def setup(self):
        super().setup()

        local_dim = 81
        state_dim = 471
        action_dim = 4
        initial_log_std = float(self.model_config.get("initial_log_std", -0.5))

        # Shared Actor network (decentralized execution)
        self.actor_net = nn.Sequential(
            nn.Linear(local_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 256),
            nn.Tanh(),
            nn.Linear(256, action_dim),
        )
        self.log_std = nn.Parameter(torch.full((action_dim,), initial_log_std, dtype=torch.float32))

        # Centralized Critic network (centralized training)
        self.critic_net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.Tanh(),
            nn.Linear(256, 256),
            nn.Tanh(),
            nn.Linear(256, 1),
        )

    def _extract_local_and_state(self, batch: Dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
        obs = batch[Columns.OBS]
        if isinstance(obs, dict):
            local_obs = obs["obs"]
            global_state = obs["state"]
        else:
            # Padded or concatenated fallback
            local_obs = obs[:, :81]
            global_state = obs[:, 81:552]

        if not isinstance(local_obs, torch.Tensor):
            local_obs = torch.as_tensor(local_obs, dtype=torch.float32)
        if not isinstance(global_state, torch.Tensor):
            global_state = torch.as_tensor(global_state, dtype=torch.float32)

        return local_obs, global_state

    def _forward(self, batch: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        local_obs, _ = self._extract_local_and_state(batch)
        mean = self.actor_net(local_obs)
        log_std = self.log_std.expand_as(mean)
        action_dist_inputs = torch.cat([mean, log_std], dim=-1)
        return {Columns.ACTION_DIST_INPUTS: action_dist_inputs}

    def _forward_inference(self, batch: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return self._forward(batch, **kwargs)

    def _forward_exploration(self, batch: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        return self._forward(batch, **kwargs)

    def _forward_train(self, batch: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        local_obs, _ = self._extract_local_and_state(batch)
        mean = self.actor_net(local_obs)
        log_std = self.log_std.expand_as(mean)
        action_dist_inputs = torch.cat([mean, log_std], dim=-1)
        return {
            Columns.ACTION_DIST_INPUTS: action_dist_inputs,
            Columns.EMBEDDINGS: mean,
        }

    def compute_values(
        self,
        batch: Dict[str, Any],
        embeddings: Optional[Any] = None,
    ) -> torch.Tensor:
        _, global_state = self._extract_local_and_state(batch)
        values = self.critic_net(global_state).squeeze(-1)
        return values

    def get_inference_action_dist_cls(self):
        return TorchDiagGaussian

    def get_exploration_action_dist_cls(self):
        return TorchDiagGaussian

    def get_train_action_dist_cls(self):
        return TorchDiagGaussian

    def act_inference_only(self, local_obs: torch.Tensor | list[float]) -> torch.Tensor:
        """Evaluate policy using solely 81-dimensional local observation vector."""
        if not isinstance(local_obs, torch.Tensor):
            local_obs = torch.tensor(local_obs, dtype=torch.float32)
        if local_obs.ndim == 1:
            local_obs = local_obs.unsqueeze(0)
        with torch.no_grad():
            mean = self.actor_net(local_obs)
        return mean.squeeze(0)
