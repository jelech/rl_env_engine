"""PolicyNetwork / ValueNetwork / ActorCritic 测试"""

import torch
import pytest

from rl_env_engine.learner.models import PolicyNetwork, ValueNetwork, ActorCritic


@pytest.fixture
def dims():
    return {"state_dim": 10, "action_dim": 20, "hidden_dim": 256}


class TestPolicyNetwork:
    def test_output_shape(self, dims):
        net = PolicyNetwork(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        x = torch.randn(32, dims["state_dim"])
        out = net(x)
        assert out.shape == (32, dims["action_dim"])

    def test_output_is_probability(self, dims):
        net = PolicyNetwork(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        x = torch.randn(4, dims["state_dim"])
        out = net(x)
        sums = out.sum(dim=-1)
        assert torch.allclose(sums, torch.ones(4), atol=1e-5)
        assert (out >= 0).all()


class TestValueNetwork:
    def test_output_shape(self, dims):
        net = ValueNetwork(dims["state_dim"], dims["hidden_dim"])
        x = torch.randn(32, dims["state_dim"])
        out = net(x)
        assert out.shape == (32, 1)


class TestActorCritic:
    def test_forward(self, dims):
        model = ActorCritic(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        x = torch.randn(8, dims["state_dim"])
        probs, values = model(x)
        assert probs.shape == (8, dims["action_dim"])
        assert values.shape == (8, 1)

    def test_act(self, dims):
        model = ActorCritic(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        x = torch.randn(4, dims["state_dim"])
        actions, log_probs, values = model.act(x)
        assert actions.shape == (4,)
        assert log_probs.shape == (4,)
        assert values.shape == (4,)
        assert (actions >= 0).all() and (actions < dims["action_dim"]).all()

    def test_evaluate(self, dims):
        model = ActorCritic(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        states = torch.randn(8, dims["state_dim"])
        actions = torch.randint(0, dims["action_dim"], (8,))
        log_probs, values, entropy = model.evaluate(states, actions)
        assert log_probs.shape == (8,)
        assert values.shape == (8,)
        assert entropy.shape == (8,)
        assert (entropy >= 0).all()

    def test_param_count(self, dims):
        """验证独立网络的参数量与博客中的计算一致"""
        model = ActorCritic(dims["state_dim"], dims["action_dim"], dims["hidden_dim"])
        total = sum(p.numel() for p in model.parameters())
        # state_dim=10, action_dim=20, hidden=256:
        # Policy: (10*256+256) + (256*256+256) + (256*20+20) = 2816 + 65792 + 5140 = 73748
        # Value:  (10*256+256) + (256*256+256) + (256*1+1)   = 2816 + 65792 + 257  = 68865
        expected = 73748 + 68865  # 142613
        assert total == expected, f"expected {expected} params, got {total}"
