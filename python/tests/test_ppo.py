"""PPO 算法测试"""

import numpy as np
import torch
import pytest

from rl_env_engine.learner.models import ActorCritic
from rl_env_engine.learner.ppo import PPO
from rl_env_engine.learner.buffer import RolloutBuffer


@pytest.fixture
def ppo_setup():
    state_dim, action_dim = 4, 5
    model = ActorCritic(state_dim, action_dim, hidden_dim=32)
    ppo = PPO(
        model=model,
        lr=1e-3,
        k_epochs=3,
        batch_size=16,
    )
    return model, ppo, state_dim, action_dim


def _fill_buffer(model, state_dim, n=64):
    buf = RolloutBuffer()
    for _ in range(n):
        state = np.random.randn(state_dim).astype(np.float32)
        state_t = torch.tensor(state).unsqueeze(0)
        with torch.no_grad():
            action, log_prob, value = model.act(state_t)
        buf.add(state, action.item(), np.random.randn(), False, log_prob.item(), value.item())
    return buf


class TestPPO:
    def test_update_returns_metrics(self, ppo_setup):
        model, ppo, state_dim, _ = ppo_setup
        buf = _fill_buffer(model, state_dim)

        metrics = ppo.update(buf)

        assert "policy_loss" in metrics
        assert "value_loss" in metrics
        assert "entropy" in metrics
        assert "num_updates" in metrics
        assert metrics["num_updates"] > 0

    def test_update_changes_weights(self, ppo_setup):
        model, ppo, state_dim, _ = ppo_setup

        params_before = [p.clone() for p in model.parameters()]
        buf = _fill_buffer(model, state_dim)
        ppo.update(buf)
        params_after = list(model.parameters())

        changed = any(
            not torch.equal(b, a)
            for b, a in zip(params_before, params_after)
        )
        assert changed, "PPO update should modify model parameters"

    def test_gradient_clipping(self, ppo_setup):
        """确认梯度裁剪生效: 参数梯度范数不超过 max_grad_norm"""
        model, ppo, state_dim, _ = ppo_setup
        buf = _fill_buffer(model, state_dim, n=128)

        # 手动调用一次 update_step 来检查梯度
        sample = buf.get_tensors()
        adv = sample.advantages
        from rl_env_engine.learner.buffer import RolloutSample
        sample = RolloutSample(
            sample.states, sample.actions, sample.returns,
            (adv - adv.mean()) / (adv.std() + 1e-8),
            sample.old_log_probs,
        )

        for batch in buf.iterate_minibatches(sample, batch_size=128):
            ppo._update_step(batch)
            break

        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.norm().item() ** 2
        total_norm = total_norm ** 0.5

        # 允许少量浮点误差
        assert total_norm <= ppo.max_grad_norm * 1.1, (
            f"grad norm {total_norm:.4f} exceeds max_grad_norm {ppo.max_grad_norm}"
        )
