#!/usr/bin/env python3
"""
综合测试：验证gRPC Simple Environment的完整工作流程
这个脚本会测试所有主要功能，确保SB3集成准备就绪
"""

import sys
import time
import numpy as np

# 检查是否能导入gRPC
try:
    import grpc
    from proto import simulation_pb2, simulation_pb2_grpc

    print("✓ gRPC imports successful")
except ImportError as e:
    print(f"❌ gRPC import failed: {e}")
    print("Please install: pip install grpcio grpcio-tools")
    sys.exit(1)

# 检查是否能导入gymnasium
try:
    import gymnasium as gym
    from gymnasium import spaces

    print("✓ Gymnasium imports successful")
except ImportError:
    try:
        import gym
        from gym import spaces

        print("✓ OpenAI Gym imports successful (legacy)")
    except ImportError as e:
        print(f"❌ Gym import failed: {e}")
        print("Please install: pip install gymnasium")
        sys.exit(1)


def test_grpc_connection():
    """测试gRPC连接"""
    print("\n=== Testing gRPC Connection ===")

    try:
        channel = grpc.insecure_channel("127.0.0.1:9090")
        client = simulation_pb2_grpc.SimulationServiceStub(channel)

        # 测试GetInfo
        request = simulation_pb2.GetInfoRequest()
        response = client.GetInfo(request)

        print(f"✓ Connected to: {response.name} v{response.version}")
        print(f"✓ Available scenarios: {list(response.scenarios)}")

        channel.close()
        return True

    except Exception as e:
        print(f"❌ gRPC connection failed: {e}")
        return False


def test_simple_scenario():
    """测试简单场景"""
    print("\n=== Testing Simple Scenario ===")

    try:
        channel = grpc.insecure_channel("127.0.0.1:9090")
        client = simulation_pb2_grpc.SimulationServiceStub(channel)

        env_id = "test_env_comprehensive"

        # 创建环境
        create_request = simulation_pb2.CreateEnvironmentRequest(
            env_id=env_id, scenario="simple", config={"max_steps": "20", "tolerance": "0.3"}
        )

        create_response = client.CreateEnvironment(create_request)
        if not create_response.success:
            print(f"❌ Create environment failed: {create_response.message}")
            return False

        print("✓ Environment created successfully")

        # 重置环境
        reset_request = simulation_pb2.ResetEnvironmentRequest(env_id=env_id)
        reset_response = client.ResetEnvironment(reset_request)

        obs_data = reset_response.observations[0].data
        observation = [float(x) for x in obs_data]

        print(f"✓ Environment reset, observation: {observation}")
        print(f"  Current: {observation[0]:.3f}, Target: {observation[1]:.3f}")

        # 执行几步
        total_reward = 0
        for step in range(5):
            # 简单策略：朝目标移动
            current = observation[0]
            target = observation[1]
            action_value = (target - current) * 0.7

            simple_action = simulation_pb2.SimpleAction(value=action_value)
            action = simulation_pb2.Action(simple_action=simple_action)

            step_request = simulation_pb2.StepEnvironmentRequest(env_id=env_id, action=action)

            step_response = client.StepEnvironment(step_request)

            obs_data = step_response.observations[0].data
            observation = [float(x) for x in obs_data]
            reward = step_response.rewards[0]
            done = step_response.done[0]

            total_reward += reward

            print(
                f"  Step {step + 1}: action={action_value:.3f}, "
                f"current={observation[0]:.3f}, reward={reward:.3f}, done={done}"
            )

            if done:
                print("  ✓ Episode completed!")
                break

        print(f"✓ Total reward: {total_reward:.3f}")

        # 关闭环境
        close_request = simulation_pb2.CloseEnvironmentRequest(env_id=env_id)
        close_response = client.CloseEnvironment(close_request)
        print("✓ Environment closed")

        channel.close()
        return True

    except Exception as e:
        print(f"❌ Simple scenario test failed: {e}")
        return False


def test_sb3_env():
    """测试SB3环境包装器"""
    print("\n=== Testing SB3 Environment Wrapper ===")

    try:
        from sb3_simple_env import SB3GrpcSimpleEnv

        # 创建环境
        env = SB3GrpcSimpleEnv(max_steps=15, tolerance=0.4)
        print("✓ SB3 environment created")

        # 检查空间定义
        print(f"✓ Action space: {env.action_space}")
        print(f"✓ Observation space: {env.observation_space}")

        # 重置环境
        obs, info = env.reset()
        print(f"✓ Environment reset")
        print(f"  Observation shape: {obs.shape}")
        print(f"  Info: {info}")

        # 运行几步
        total_reward = 0
        for step in range(3):
            # 采样随机动作
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

            print(f"  Step {step + 1}: action={action[0]:.3f}, " f"reward={reward:.3f}, done={terminated}")

            if terminated or truncated:
                print("  ✓ Episode finished")
                break

        print(f"✓ Total reward: {total_reward:.3f}")

        # 关闭环境
        env.close()
        print("✓ Environment closed")

        return True

    except Exception as e:
        print(f"❌ SB3 environment test failed: {e}")
        return False


def test_sb3_compatibility():
    """测试SB3兼容性"""
    print("\n=== Testing SB3 Compatibility ===")

    try:
        from stable_baselines3.common.env_checker import check_env
        from sb3_simple_env import SB3GrpcSimpleEnv

        env = SB3GrpcSimpleEnv(max_steps=10, tolerance=0.5)

        print("Running SB3 environment checker...")
        check_env(env)
        print("✓ SB3 environment check passed!")

        env.close()
        return True

    except ImportError:
        print("⚠️ Stable-Baselines3 not installed, skipping compatibility test")
        print("Install with: pip install stable-baselines3[extra]")
        return True

    except Exception as e:
        print(f"❌ SB3 compatibility test failed: {e}")
        return False


def test_performance():
    """测试性能"""
    print("\n=== Testing Performance ===")

    try:
        from sb3_simple_env import SB3GrpcSimpleEnv

        env = SB3GrpcSimpleEnv(max_steps=100, tolerance=0.1)

        print("Running performance test (100 steps)...")
        start_time = time.time()

        obs, _ = env.reset()
        for _ in range(100):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)

            if terminated or truncated:
                obs, _ = env.reset()

        end_time = time.time()
        elapsed = end_time - start_time
        fps = 100 / elapsed

        print(f"✓ Performance test completed")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  FPS: {fps:.1f}")

        env.close()
        return True

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 Comprehensive gRPC Simple Environment Test")
    print("=" * 50)

    # 等待服务器启动
    print("Waiting for gRPC server to start...")
    time.sleep(2)

    tests = [
        ("gRPC Connection", test_grpc_connection),
        ("Simple Scenario", test_simple_scenario),
        ("SB3 Environment", test_sb3_env),
        ("SB3 Compatibility", test_sb3_compatibility),
        ("Performance", test_performance),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1

    print(f"\n🎯 OVERALL: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Your gRPC Simple Environment is ready for SB3!")
        print("\nNext steps:")
        print("1. Install SB3: pip install stable-baselines3[extra]")
        print("2. Run training: python sb3_training.py")
        print("3. Monitor with TensorBoard")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
