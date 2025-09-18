"""
Simulation Gym Environment - Python Client

This module provides a Python client that mimics OpenAI Gym interface
for interacting with the Go simulation server via HTTP API.
"""

import requests
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import json


class SimulationEnv:
    """
    OpenAI Gym-compatible environment wrapper for simulation server.
    """

    def __init__(self, server_url: str = "http://localhost:8080"):
        """
        Initialize the simulation environment.

        Args:
            server_url: URL of the simulation server
        """
        self.server_url = server_url.rstrip("/")
        self.env_id: Optional[str] = None
        self.observation_space = None
        self.action_space = None

    def create_env(self, env_id: str, scenario: str, config: Dict[str, Any]) -> bool:
        """
        Create a new environment on the server.

        Args:
            env_id: Unique identifier for the environment
            scenario: Scenario type (e.g., 'simple')
            config: Environment configuration

        Returns:
            bool: True if environment created successfully
        """
        try:
            response = requests.post(
                f"{self.server_url}/create", json={"env_id": env_id, "scenario": scenario, "config": config}, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if result.get("success", False):
                self.env_id = env_id
                return True
            else:
                print(f"Failed to create environment: {result.get('message', 'Unknown error')}")
                return False

        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False

    def reset(self) -> np.ndarray:
        """
        Reset the environment and return initial observation.

        Returns:
            np.ndarray: Initial observation
        """
        if self.env_id is None:
            raise ValueError("Environment not created. Call create_env() first.")

        try:
            response = requests.post(f"{self.server_url}/reset", json={"env_id": self.env_id}, timeout=30)
            response.raise_for_status()

            result = response.json()
            observation = np.array(result["observation"])
            return observation

        except requests.RequestException as e:
            raise RuntimeError(f"Reset failed: {e}")

    def step(self, action: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Execute one step in the environment.

        Args:
            action: Action to take

        Returns:
            Tuple of (observation, reward, done, info)
        """
        if self.env_id is None:
            raise ValueError("Environment not created. Call create_env() first.")

        try:
            response = requests.post(
                f"{self.server_url}/step", json={"env_id": self.env_id, "action": action}, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            observation = np.array(result["observation"])
            reward = np.array(result["reward"])
            done = np.array(result["done"])
            info = result["info"]

            return observation, reward, done, info

        except requests.RequestException as e:
            raise RuntimeError(f"Step failed: {e}")

    def close(self) -> bool:
        """
        Close the environment.

        Returns:
            bool: True if closed successfully
        """
        if self.env_id is None:
            return True

        try:
            response = requests.post(f"{self.server_url}/close", json={"env_id": self.env_id}, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("success", False):
                self.env_id = None
                return True
            else:
                print(f"Failed to close environment: {result.get('message', 'Unknown error')}")
                return False

        except requests.RequestException as e:
            print(f"Close request failed: {e}")
            return False

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the server and available scenarios.

        Returns:
            Dict containing server information
        """
        try:
            response = requests.get(f"{self.server_url}/info", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to get server info: {e}")

    def is_server_alive(self) -> bool:
        """
        Check if the server is alive and responding.

        Returns:
            bool: True if server is responding
        """
        try:
            response = requests.get(f"{self.server_url}/", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False


def example_simple_training():
    """
    Example of how to use the simple environment for RL training.
    """
    # Initialize environment
    env = SimulationEnv(server_url="http://localhost:8080")

    # Check if server is alive
    if not env.is_server_alive():
        print("Error: Simulation server is not running!")
        print("Please start the server with: go run examples/server/main.go")
        return

    # Get server info
    info = env.get_server_info()
    print(f"Server info: {info}")

    # Create simple environment
    config = {"max_steps": 100, "tolerance": 0.1}
    if not env.create_env("simple_rl_env", "simple", config):
        print("Failed to create environment")
        return

    try:
        # Reset environment
        print("Resetting environment...")
        obs = env.reset()
        print(f"Initial observation: {obs}")

        # Run training episodes
        num_episodes = 5
        for episode in range(num_episodes):
            print(f"\n--- Episode {episode + 1} ---")

            episode_reward = 0
            step_count = 0

            # Reset for new episode
            obs = env.reset()

            while True:
                # Create random action (in real RL, this would be from your agent)
                action = np.random.uniform(-2.0, 2.0)  # Random action for simple scenario

                # Take step
                obs, reward, done, info = env.step(action)

                episode_reward += np.sum(reward)
                step_count += 1

                print(
                    f"Step {step_count}: action={action:.2f}, reward={np.sum(reward):.2f}, done={done[0] if len(done) > 0 else False}"
                )

                # Check if episode is done
                if len(done) > 0 and done[0]:
                    break

                # Limit max steps per episode
                if step_count >= 50:
                    break

            print(f"Episode {episode + 1} finished: total_reward={episode_reward:.2f}, steps={step_count}")

    finally:
        # Clean up
        env.close()
        print("Environment closed")


if __name__ == "__main__":
    # Run example
    example_simple_training()
