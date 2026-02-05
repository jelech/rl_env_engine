from python.src.rl_env_engine.server import create_app, BaseScenario, run_server


class BrDriverAllocationScenario(BaseScenario):
    def create_environment(self, config):
        return None

    def reset(self, env, **kwargs):
        return env.reset(**kwargs)

    def step(self, env, action, **kwargs):
        return env.step(action, **kwargs)


if __name__ == "__main__":
    app = create_app(
        scenarios=[BrDriverAllocationScenario()],
        scenario_name="br_driver_allocation",
        enable_discovery=True,
        max_concurrent_tasks=10,
        use_process_isolation=True,
    )
    run_server(app, port=8000)
