"""RolloutBuffer + GAE 测试"""

import numpy as np
import torch
import pytest

from rl_env_engine.learner.buffer import RolloutBuffer


class TestRolloutBuffer:
    def test_add_and_size(self):
        buf = RolloutBuffer()
        assert buf.size() == 0

        for i in range(10):
            buf.add(
                state=np.array([1.0, 2.0]),
                action=0,
                reward=1.0,
                done=False,
                log_prob=-0.5,
                value=0.9,
            )
        assert buf.size() == 10

    def test_clear(self):
        buf = RolloutBuffer()
        for _ in range(5):
            buf.add(np.zeros(4), 0, 1.0, False, -0.5, 0.9)
        buf.clear()
        assert buf.size() == 0

    def test_gae_simple(self):
        """验证 GAE 计算: 简单的 3-step episode"""
        buf = RolloutBuffer()
        buf.add(np.zeros(2), 0, 1.0, False, -0.5, 0.5)
        buf.add(np.zeros(2), 1, 1.0, False, -0.3, 0.6)
        buf.add(np.zeros(2), 0, 1.0, True,  -0.4, 0.7)

        returns, advantages = buf.compute_returns_and_advantages(
            gamma=0.99, gae_lambda=0.95, last_value=0.0
        )

        assert len(returns) == 3
        assert len(advantages) == 3
        # done=True 的最后一步, next_non_terminal=0, delta = r - V
        assert abs(advantages[2] - (1.0 - 0.7)) < 1e-5

    def test_gae_done_boundary(self):
        """验证 done=True 正确截断折扣累积"""
        buf = RolloutBuffer()
        # Episode 1
        buf.add(np.zeros(2), 0, 1.0, False, -0.5, 0.5)
        buf.add(np.zeros(2), 0, 1.0, True,  -0.5, 0.5)
        # Episode 2
        buf.add(np.zeros(2), 0, 2.0, False, -0.5, 0.5)
        buf.add(np.zeros(2), 0, 2.0, True,  -0.5, 0.5)

        returns, advantages = buf.compute_returns_and_advantages(gamma=0.99, gae_lambda=0.95)

        # done=True 处截断，episode 2 的 advantage 应该 > episode 1
        assert advantages[2] > advantages[0]

    def test_get_tensors(self):
        buf = RolloutBuffer()
        for _ in range(20):
            buf.add(np.random.randn(4), 0, 1.0, False, -0.5, 0.9)

        sample = buf.get_tensors()
        assert sample.states.shape == (20, 4)
        assert sample.actions.shape == (20,)
        assert sample.returns.shape == (20,)
        assert sample.advantages.shape == (20,)
        assert sample.old_log_probs.shape == (20,)

    def test_minibatch_iterator(self):
        buf = RolloutBuffer()
        for _ in range(100):
            buf.add(np.random.randn(4), 0, 1.0, False, -0.5, 0.9)

        sample = buf.get_tensors()
        batches = list(buf.iterate_minibatches(sample, batch_size=32))

        assert len(batches) == 4  # ceil(100/32) = 4
        total = sum(b.states.shape[0] for b in batches)
        assert total == 100
