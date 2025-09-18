#!/usr/bin/env python3
"""
gRPC客户端示例，用于与仿真服务器进行通信
"""
import grpc


try:
    from . import simulation_pb2, simulation_pb2_grpc  # type: ignore
except Exception:  # pragma: no cover
    try:
        import simulation_pb2  # type: ignore
        import simulation_pb2_grpc  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Cannot import simulation_pb2. Generate it via protoc or ensure package is installed."  # noqa: E501
        ) from e


class SimulationGrpcClient:
    def __init__(self, server_address="localhost:9090"):
        """
        初始化gRPC客户端

        Args:
            server_address: gRPC服务器地址，默认为localhost:9090
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None

    def connect(self):
        """连接到gRPC服务器"""
        try:
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = simulation_pb2_grpc.SimulationServiceStub(self.channel)
            print(f"Connected to gRPC server at {self.server_address}")
            return True
        except Exception as e:
            print(f"Failed to connect to gRPC server: {e}")
            return False

    def disconnect(self):
        """断开与gRPC服务器的连接"""
        if self.channel:
            self.channel.close()
            print("Disconnected from gRPC server")

    def get_info(self):
        """获取服务器信息"""
        try:
            request = simulation_pb2.GetInfoRequest()
            response = self.stub.GetInfo(request)
            return {
                "scenarios": list(response.scenarios),
                "env_ids": list(response.env_ids),
                "info": dict(response.info),
                "version": response.version,
                "name": response.name,
            }
        except grpc.RpcError as e:
            print(f"gRPC error in get_info: {e}")
            return None

    def create_environment(self, env_id, scenario, config=None):
        """
        创建仿真环境

        Args:
            env_id: 环境ID
            scenario: 场景名称
            config: 配置字典
        """
        try:
            if config is None:
                config = {}

            request = simulation_pb2.CreateEnvironmentRequest(env_id=env_id, scenario=scenario, config=config)
            response = self.stub.CreateEnvironment(request)
            return {"success": response.success, "message": response.message}
        except grpc.RpcError as e:
            print(f"gRPC error in create_environment: {e}")
            return None

    def reset_environment(self, env_id):
        """
        重置环境

        Args:
            env_id: 环境ID
        """
        try:
            request = simulation_pb2.ResetEnvironmentRequest(env_id=env_id)
            response = self.stub.ResetEnvironment(request)

            observations = []
            for obs in response.observations:
                observations.append({"data": list(obs.data), "metadata": dict(obs.metadata)})

            return {"observations": observations, "info": dict(response.info)}
        except grpc.RpcError as e:
            print(f"gRPC error in reset_environment: {e}")
            return None

    def step_environment(self, env_id, action_value):
        """
        执行仿真步骤

        Args:
            env_id: 环境ID
            action_value: 简单动作值，例如 1.5
        """
        try:
            # 创建SimpleAction
            simple_action = simulation_pb2.SimpleAction(value=action_value)
            action = simulation_pb2.Action(simple_action=simple_action)

            request = simulation_pb2.StepEnvironmentRequest(env_id=env_id, action=action)
            response = self.stub.StepEnvironment(request)

            observations = []
            for obs in response.observations:
                observations.append({"data": list(obs.data), "metadata": dict(obs.metadata)})

            return {
                "observations": observations,
                "rewards": list(response.rewards),
                "done": list(response.done),
                "info": dict(response.info),
            }
        except grpc.RpcError as e:
            print(f"gRPC error in step_environment: {e}")
            return None

    def close_environment(self, env_id):
        """
        关闭环境

        Args:
            env_id: 环境ID
        """
        try:
            request = simulation_pb2.CloseEnvironmentRequest(env_id=env_id)
            response = self.stub.CloseEnvironment(request)
            return {"success": response.success, "message": response.message}
        except grpc.RpcError as e:
            print(f"gRPC error in close_environment: {e}")
            return None


def demo_simple_simulation():
    """演示简单仿真的完整流程"""
    client = SimulationGrpcClient()

    if not client.connect():
        return

    try:
        # 1. 获取服务器信息
        print("=== 获取服务器信息 ===")
        info = client.get_info()
        if info:
            print(f"服务器名称: {info['name']}")
            print(f"版本: {info['version']}")
            print(f"可用场景: {info['scenarios']}")
            print(f"活跃环境: {info['env_ids']}")

        # 2. 创建环境
        print("\n=== 创建环境 ===")
        env_id = "test_simple_env"
        config = {"max_steps": "100", "tolerance": "0.1"}

        create_result = client.create_environment(env_id, "simple", config)
        if create_result and create_result["success"]:
            print(f"环境创建成功: {create_result['message']}")
        else:
            print(f"环境创建失败: {create_result}")
            return

        # 3. 重置环境
        print("\n=== 重置环境 ===")
        reset_result = client.reset_environment(env_id)
        if reset_result:
            print(f"环境重置成功，观察数量: {len(reset_result['observations'])}")
            if reset_result["observations"]:
                print(f"第一个观察的数据长度: {len(reset_result['observations'][0]['data'])}")

        # 4. 执行几步仿真
        print("\n=== 执行仿真步骤 ===")
        for step in range(3):
            # 创建示例动作（这里使用随机值，实际应用中应该基于观察来决定）
            action_value = 1.0 + step * 0.5  # 简单的标量动作

            step_result = client.step_environment(env_id, action_value)
            if step_result:
                print(f"步骤 {step + 1}:")
                print(f"  动作值: {action_value}")
                print(f"  奖励: {step_result['rewards']}")
                print(f"  完成状态: {step_result['done']}")
                print(f"  观察数量: {len(step_result['observations'])}")
            else:
                print(f"步骤 {step + 1} 执行失败")
                break

        # 5. 关闭环境
        print("\n=== 关闭环境 ===")
        close_result = client.close_environment(env_id)
        if close_result and close_result["success"]:
            print(f"环境关闭成功: {close_result['message']}")

    finally:
        client.disconnect()


if __name__ == "__main__":
    print("gRPC仿真客户端演示")
    print("确保gRPC服务器正在运行在localhost:9090")
    print("-" * 50)

    demo_simple_simulation()
