#!/usr/bin/env python3
"""
测试从Go端获取action space和observation space的功能
"""

from rl_env_engine_client import SB3GrpcSimpleEnv


def test_spaces_from_go():
    """测试从Go端获取空间定义"""
    print("=== 测试从Go端获取空间定义 ===")

    try:
        # 创建环境，它会自动从Go端获取空间定义
        env = SB3GrpcSimpleEnv(host="127.0.0.1", port=19090, max_steps=20, tolerance=0.1)

        print(f"Action Space: {env.action_space}")
        print(f"  - Type: {type(env.action_space)}")
        print(f"  - Low: {env.action_space.low}")
        print(f"  - High: {env.action_space.high}")
        print(f"  - Shape: {env.action_space.shape}")
        print(f"  - Dtype: {env.action_space.dtype}")

        print(f"\nObservation Space: {env.observation_space}")
        print(f"  - Type: {type(env.observation_space)}")
        print(f"  - Low: {env.observation_space.low}")
        print(f"  - High: {env.observation_space.high}")
        print(f"  - Shape: {env.observation_space.shape}")
        print(f"  - Dtype: {env.observation_space.dtype}")

        # 测试环境重置
        obs, info = env.reset()
        print(f"\nReset observation: {obs}")
        print(f"Reset info: {info}")

        # 测试一步
        action = env.action_space.sample()
        print(f"\nSample action: {action}")

        obs, reward, terminated, truncated, info = env.step(action)
        print(f"Step result:")
        print(f"  - Observation: {obs}")
        print(f"  - Reward: {reward}")
        print(f"  - Terminated: {terminated}")
        print(f"  - Info: {info}")

        env.close()
        print("\n✅ 测试成功！空间定义成功从Go端获取")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_spaces_from_go()
