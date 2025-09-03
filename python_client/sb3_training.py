#!/usr/bin/env python3
"""
使用Stable Baselines 3训练简单gRPC环境的示例

要求：
pip install stable-baselines3[extra] gymnasium grpcio grpcio-tools

运行前确保gRPC服务器正在运行：
make build-grpc && ./bin/grpc_server_example
"""

import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import PPO, A2C, SAC
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import EvalCallback
from sb3_simple_env import SB3GrpcSimpleEnv


def train_ppo_agent():
    """使用PPO算法训练agent"""
    print("Starting PPO training...")

    # 创建环境
    env = SB3GrpcSimpleEnv(max_steps=50, tolerance=0.2)

    # 检查环境是否符合SB3规范
    print("Checking environment...")
    check_env(env)
    print("Environment check passed!")

    # 包装环境以记录训练数据
    env = Monitor(env)

    try:
        # 创建PPO agent
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            tensorboard_log="./ppo_simple_tensorboard/",
        )

        # 训练
        print("Training PPO agent...")
        model.learn(total_timesteps=50000, tb_log_name="ppo_simple_run")

        # 保存模型
        model.save("ppo_simple_env")
        print("Model saved as 'ppo_simple_env'")

        # 测试训练好的agent
        print("\nTesting trained agent...")
        test_trained_agent(model, env)

    finally:
        env.close()


def train_a2c_agent():
    """使用A2C算法训练agent"""
    print("Starting A2C training...")

    # 创建环境
    env = SB3GrpcSimpleEnv(max_steps=30, tolerance=0.3)
    env = Monitor(env)

    try:
        # 创建A2C agent
        model = A2C(
            "MlpPolicy",
            env,
            verbose=1,
            learning_rate=7e-4,
            n_steps=5,
            gamma=0.99,
            gae_lambda=1.0,
            ent_coef=0.0,
            vf_coef=0.25,
            max_grad_norm=0.5,
            tensorboard_log="./a2c_simple_tensorboard/",
        )

        # 训练
        print("Training A2C agent...")
        model.learn(total_timesteps=30000, tb_log_name="a2c_simple_run")

        # 保存模型
        model.save("a2c_simple_env")
        print("Model saved as 'a2c_simple_env'")

        # 测试训练好的agent
        print("\nTesting trained agent...")
        test_trained_agent(model, env)

    finally:
        env.close()


def test_trained_agent(model, env, n_episodes=5):
    """测试训练好的agent"""
    episode_rewards = []
    episode_lengths = []

    for episode in range(n_episodes):
        obs, _ = env.reset()
        episode_reward = 0
        steps = 0

        print(f"\nEpisode {episode + 1}:")
        print(f"  Initial: current={obs[0]:.3f}, target={obs[1]:.3f}")

        while True:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            steps += 1

            print(f"  Step {steps}: action={action[0]:.3f}, " f"current={obs[0]:.3f}, reward={reward:.3f}")

            if terminated or truncated:
                break

        episode_rewards.append(episode_reward)
        episode_lengths.append(steps)

        print(f"  Episode reward: {episode_reward:.3f}, steps: {steps}")

        success = abs(obs[0] - obs[1]) <= obs[4]  # current接近target且在tolerance内
        print(f"  Success: {success}")

    print(f"\nAverage reward: {np.mean(episode_rewards):.3f} ± {np.std(episode_rewards):.3f}")
    print(f"Average length: {np.mean(episode_lengths):.1f} ± {np.std(episode_lengths):.1f}")


def compare_algorithms():
    """比较不同算法的性能"""
    print("Comparing different algorithms...")

    algorithms = {
        "PPO": lambda env: PPO("MlpPolicy", env, verbose=0),
        "A2C": lambda env: A2C("MlpPolicy", env, verbose=0),
    }

    results = {}

    for name, algo_fn in algorithms.items():
        print(f"\nTraining {name}...")

        # 创建环境
        env = SB3GrpcSimpleEnv(max_steps=40, tolerance=0.25)
        env = Monitor(env)

        try:
            # 训练
            model = algo_fn(env)
            model.learn(total_timesteps=20000)

            # 测试
            episode_rewards = []
            for _ in range(10):
                obs, _ = env.reset()
                episode_reward = 0

                while True:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, terminated, truncated, _ = env.step(action)
                    episode_reward += reward

                    if terminated or truncated:
                        break

                episode_rewards.append(episode_reward)

            results[name] = {"mean": np.mean(episode_rewards), "std": np.std(episode_rewards)}

            print(f"{name} - Average reward: {results[name]['mean']:.3f} ± {results[name]['std']:.3f}")

        finally:
            env.close()

    # 打印比较结果
    print("\n" + "=" * 50)
    print("ALGORITHM COMPARISON RESULTS")
    print("=" * 50)
    for name, result in results.items():
        print(f"{name:>10}: {result['mean']:>8.3f} ± {result['std']:>6.3f}")


def hyperparameter_tuning():
    """简单的超参数调优示例"""
    print("Hyperparameter tuning for PPO...")

    learning_rates = [1e-4, 3e-4, 1e-3]
    results = {}

    for lr in learning_rates:
        print(f"\nTesting learning rate: {lr}")

        env = SB3GrpcSimpleEnv(max_steps=35, tolerance=0.2)
        env = Monitor(env)

        try:
            model = PPO("MlpPolicy", env, learning_rate=lr, verbose=0)

            model.learn(total_timesteps=15000)

            # 评估
            episode_rewards = []
            for _ in range(5):
                obs, _ = env.reset()
                episode_reward = 0

                while True:
                    action, _ = model.predict(obs, deterministic=True)
                    obs, reward, terminated, truncated, _ = env.step(action)
                    episode_reward += reward

                    if terminated or truncated:
                        break

                episode_rewards.append(episode_reward)

            avg_reward = np.mean(episode_rewards)
            results[lr] = avg_reward

            print(f"Learning rate {lr}: {avg_reward:.3f}")

        finally:
            env.close()

    # 找到最佳学习率
    best_lr = max(results, key=results.get)
    print(f"\nBest learning rate: {best_lr} (reward: {results[best_lr]:.3f})")


def main():
    """主函数"""
    print("=== SB3 gRPC Simple Environment Training ===")
    print()
    print("Make sure the gRPC server is running:")
    print("  make build-grpc && ./bin/grpc_server_example")
    print()

    # 选择要运行的训练
    print("Choose training option:")
    print("1. Train PPO agent")
    print("2. Train A2C agent")
    print("3. Compare algorithms")
    print("4. Hyperparameter tuning")
    print("5. Quick test")

    choice = input("Enter choice (1-5): ").strip()

    if choice == "1":
        train_ppo_agent()
    elif choice == "2":
        train_a2c_agent()
    elif choice == "3":
        compare_algorithms()
    elif choice == "4":
        hyperparameter_tuning()
    elif choice == "5":
        quick_test()
    else:
        print("Invalid choice. Running quick test...")
        quick_test()


def quick_test():
    """快速测试环境是否工作"""
    print("Quick test of the environment...")

    env = SB3GrpcSimpleEnv(max_steps=20, tolerance=0.4)

    try:
        # 检查环境
        check_env(env)
        print("✓ Environment check passed")

        # 测试几个episodes
        for episode in range(3):
            obs, info = env.reset()
            episode_reward = 0
            steps = 0

            print(f"\nEpisode {episode + 1}:")
            print(f"  Start: current={obs[0]:.3f}, target={obs[1]:.3f}")

            while True:
                # 随机动作
                action = env.action_space.sample()
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                steps += 1

                if terminated or truncated:
                    break

            print(f"  End: current={obs[0]:.3f}, steps={steps}, reward={episode_reward:.3f}")

        print("\n✓ Environment is working correctly!")

    finally:
        env.close()


if __name__ == "__main__":
    main()
