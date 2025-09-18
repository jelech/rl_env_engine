"""
Advanced Reinforcement Learning Example using Stable-Baselines3

This example shows how to integrate the simulation environment with
popular RL libraries like stable-baselines3.
"""

import gym
import numpy as np
from gym import spaces
from typing import Dict, Any, Tuple
import requests

from simulation_gym import SimulationEnv


class SimulationGymWrapper(gym.Env):
    """
    OpenAI Gym wrapper for the simulation environment.

    This wrapper makes the simulation environment compatible with
    standard RL libraries like stable-baselines3.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        scenario: str = "simple",
        config: Dict[str, Any] = None,
        env_id: str = "sim_env",
    ):
        """
        Initialize the gym wrapper.

        Args:
            server_url: URL of the simulation server
            scenario: Scenario type
            config: Environment configuration
            env_id: Environment identifier
        """
        super().__init__()

        self.sim_env = SimulationEnv(server_url)
        self.scenario = scenario
        self.config = config or self._get_default_config()
        self.env_id = env_id

        # These will be set after first reset
        self.observation_space = None
        self.action_space = None
        self._setup_spaces()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for simple scenario."""
        return {
            "max_steps": 100,
            "tolerance": 0.1,
        }

    def _setup_spaces(self):
        """Setup observation and action spaces."""
        # For simple scenario, we'll define simple spaces
        # In practice, these should be determined from the actual environment

        # Observation space: assume max 100 SKUs, each with 10 features
        max_skus = 100
        features_per_sku = 10
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(max_skus, features_per_sku), dtype=np.float32
        )

        # Action space: multiplier for each SKU (between 0.1 and 2.0)
        self.action_space = spaces.Box(low=0.1, high=2.0, shape=(max_skus,), dtype=np.float32)

    def reset(self) -> np.ndarray:
        """Reset the environment."""
        # Create environment if not exists
        if self.sim_env.env_id is None:
            if not self.sim_env.create_env(self.env_id, self.scenario, self.config):
                raise RuntimeError("Failed to create simulation environment")

        # Reset and get observation
        obs = self.sim_env.reset()

        # Adjust observation space based on actual observation
        if self.observation_space is None or obs.shape != self.observation_space.shape:
            self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=obs.shape, dtype=np.float32)

            # Adjust action space to match number of SKUs
            num_skus = obs.shape[0]
            self.action_space = spaces.Box(low=0.1, high=2.0, shape=(num_skus,), dtype=np.float32)

        return obs.astype(np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """Execute one step in the environment."""
        # Convert action array to SKU actions dictionary
        sku_actions = {f"sku_{i:03d}": float(action[i]) for i in range(len(action))}

        # Execute step
        obs, rewards, done, info = self.sim_env.step({"sku_actions": sku_actions})

        # Convert to gym format
        total_reward = float(np.sum(rewards))
        is_done = bool(done[0]) if len(done) > 0 else False

        return obs.astype(np.float32), total_reward, is_done, info

    def close(self):
        """Close the environment."""
        if self.sim_env:
            self.sim_env.close()

    def render(self, mode="human"):
        """Render the environment (optional)."""
        # For now, just print some info
        if mode == "human":
            print("Simulation environment (rendering not implemented)")


def train_with_stable_baselines3():
    """
    Example of training an RL agent using stable-baselines3.

    Note: You need to install stable-baselines3:
    pip install stable-baselines3[extra]
    """
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.env_checker import check_env
        from stable_baselines3.common.callbacks import EvalCallback
    except ImportError:
        print("stable-baselines3 not installed. Install with:")
        print("pip install stable-baselines3[extra]")
        return

    # Check if server is running
    sim_env = SimulationEnv()
    if not sim_env.is_server_alive():
        print("Error: Simulation server is not running!")
        print("Please start the server with: go run cmd/server/main.go")
        return

    # Create environment
    config = {
        "max_steps": 100,
        "tolerance": 0.1,
    }

    env = SimulationGymWrapper(server_url="http://localhost:8080", scenario="simple", config=config, env_id="sb3_env")

    try:
        # Check environment
        print("Checking environment...")
        check_env(env)
        print("Environment check passed!")

        # Create PPO agent
        print("Creating PPO agent...")
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
            ent_coef=0.0,
            vf_coef=0.5,
            max_grad_norm=0.5,
            tensorboard_log="./ppo_simulation_tensorboard/",
        )

        # Train the agent
        print("Starting training...")
        total_timesteps = 10000  # Start with small number for testing
        model.learn(total_timesteps=total_timesteps, progress_bar=True)

        # Save the model
        model_path = "ppo_simulation_model"
        model.save(model_path)
        print(f"Model saved to {model_path}")

        # Test the trained agent
        print("\nTesting trained agent...")
        obs = env.reset()
        total_reward = 0

        for step in range(50):
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            total_reward += reward

            if done:
                break

        print(f"Test episode finished. Total reward: {total_reward:.2f}")

    finally:
        env.close()


def train_with_custom_algorithm():
    """
    Example of training with a simple custom algorithm (Random Search).
    """
    # Check if server is running
    sim_env = SimulationEnv()
    if not sim_env.is_server_alive():
        print("Error: Simulation server is not running!")
        print("Please start the server with: go run cmd/server/main.go")
        return

    env = SimulationGymWrapper(env_id="custom_training_env")

    try:
        print("Training with custom random search algorithm...")

        best_reward = float("-inf")
        best_params = None

        # Random search for 100 iterations
        for iteration in range(100):
            # Reset environment
            obs = env.reset()

            # Generate random policy parameters
            # For simplicity, use a single multiplier for all SKUs
            multiplier = np.random.uniform(0.5, 1.5)

            total_reward = 0
            episode_length = 0

            # Run episode
            while episode_length < 30:  # Max 30 steps per episode
                # Create action (same multiplier for all SKUs)
                num_skus = obs.shape[0]
                action = np.full(num_skus, multiplier, dtype=np.float32)

                obs, reward, done, info = env.step(action)
                total_reward += reward
                episode_length += 1

                if done:
                    break

            # Update best parameters
            if total_reward > best_reward:
                best_reward = total_reward
                best_params = {"multiplier": multiplier}
                print(f"Iteration {iteration}: New best reward {best_reward:.2f} with multiplier {multiplier:.3f}")

        print(f"\nTraining completed!")
        print(f"Best reward: {best_reward:.2f}")
        print(f"Best parameters: {best_params}")

        # Test best parameters
        print("\nTesting best parameters...")
        obs = env.reset()
        total_reward = 0

        for step in range(30):
            num_skus = obs.shape[0]
            action = np.full(num_skus, best_params["multiplier"], dtype=np.float32)
            obs, reward, done, info = env.step(action)
            total_reward += reward

            if done:
                break

        print(f"Test with best parameters: Total reward {total_reward:.2f}")

    finally:
        env.close()


if __name__ == "__main__":
    print("=== Simulation RL Training Examples ===\n")

    print("1. Training with Stable-Baselines3 (PPO)")
    print("2. Training with Custom Algorithm (Random Search)")

    choice = input("\nEnter your choice (1 or 2): ").strip()

    if choice == "1":
        train_with_stable_baselines3()
    elif choice == "2":
        train_with_custom_algorithm()
    else:
        print("Invalid choice. Running custom algorithm by default.")
        train_with_custom_algorithm()
