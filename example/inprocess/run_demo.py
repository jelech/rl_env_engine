#!/usr/bin/env python3
"""
InProcessSDK Demo - 展示 Python / Cython / C 三种环境接入方式

用法:
    # 1. 编译 Cython 和 C 环境
    cd envs && make && cd ..

    # 2. 运行 demo
    python run_demo.py --mode python          # 纯 Python 环境
    python run_demo.py --mode cython          # Cython 环境
    python run_demo.py --mode c               # C 共享库环境
    python run_demo.py --mode benchmark       # 三者性能对比

    # 参数
    --num-envs   4      # 并行环境数
    --num-steps  2000   # 总 step 数
    --parallel   thread # sequential / thread / subprocess
"""

import os
import sys
import time
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python", "src"))
from rl_env_engine.client.inprocess_sdk import InProcessSDK


def run_training_loop(sdk, num_steps, num_envs, config):
    """模拟标准 RL 训练循环，返回 (总 reward, 耗时秒)。"""
    sdk.create_sessions(batch_size=num_envs, config=config)
    sdk.batch_reset()

    total_reward = 0.0
    t0 = time.perf_counter()

    for step in range(num_steps):
        actions = [np.random.uniform(-1, 1) for _ in range(num_envs)]
        results = sdk.batch_step(actions)

        for obs, reward, done, truncated, info in results:
            total_reward += reward

        if step > 0 and step % (num_steps // 5) == 0:
            eps = num_envs * step / (time.perf_counter() - t0)
            print(f"  step {step}/{num_steps}, "
                  f"avg_reward={total_reward / (num_envs * step):.4f}, "
                  f"throughput={eps:.0f} steps/s")

    elapsed = time.perf_counter() - t0
    sdk.close()
    return total_reward, elapsed


def demo_python(args):
    from envs.tracker_python import TrackerEnv

    print(f"=== Python 环境 (parallel={args.parallel}) ===")
    sdk = InProcessSDK(TrackerEnv, num_envs=args.num_envs, parallel=args.parallel)
    total, elapsed = run_training_loop(
        sdk, args.num_steps, args.num_envs, {"target": 1.0}
    )
    total_steps = args.num_envs * args.num_steps
    print(f"  Done: {total_steps} steps in {elapsed:.3f}s "
          f"({total_steps / elapsed:.0f} steps/s)\n")
    return elapsed


def demo_cython(args):
    try:
        from envs.tracker_cython import TrackerEnv
    except ImportError:
        print("Cython 环境未编译，请先执行: cd envs && python setup.py build_ext --inplace")
        return None

    print(f"=== Cython 环境 (parallel={args.parallel}) ===")
    sdk = InProcessSDK(TrackerEnv, num_envs=args.num_envs, parallel=args.parallel)
    total, elapsed = run_training_loop(
        sdk, args.num_steps, args.num_envs, {"target": 1.0}
    )
    total_steps = args.num_envs * args.num_steps
    print(f"  Done: {total_steps} steps in {elapsed:.3f}s "
          f"({total_steps / elapsed:.0f} steps/s)\n")
    return elapsed


def demo_c(args):
    envs_dir = os.path.join(os.path.dirname(__file__), "envs")
    lib_name = "libtracker.dylib" if sys.platform == "darwin" else "libtracker.so"
    lib_path = os.path.join(envs_dir, lib_name)

    if not os.path.exists(lib_path):
        print(f"C 共享库未编译，请先执行: cd envs && make")
        return None

    print(f"=== C 环境 (parallel={args.parallel}) ===")
    sdk = InProcessSDK.from_c_lib(lib_path, num_envs=args.num_envs, parallel=args.parallel)
    total, elapsed = run_training_loop(
        sdk, args.num_steps, args.num_envs, {"target": 1.0}
    )
    total_steps = args.num_envs * args.num_steps
    print(f"  Done: {total_steps} steps in {elapsed:.3f}s "
          f"({total_steps / elapsed:.0f} steps/s)\n")
    return elapsed


def demo_benchmark(args):
    print("=" * 60)
    print(f"Benchmark: {args.num_envs} envs × {args.num_steps} steps")
    print(f"Parallel mode: {args.parallel}")
    print("=" * 60 + "\n")

    results = {}
    for name, fn in [("Python", demo_python), ("Cython", demo_cython), ("C", demo_c)]:
        elapsed = fn(args)
        if elapsed is not None:
            results[name] = elapsed

    if not results:
        return

    print("=" * 60)
    print("Summary:")
    baseline = results.get("Python", list(results.values())[0])
    for name, elapsed in results.items():
        speedup = baseline / elapsed if elapsed > 0 else 0
        total_steps = args.num_envs * args.num_steps
        print(f"  {name:8s}: {elapsed:.3f}s  "
              f"({total_steps / elapsed:8.0f} steps/s)  "
              f"speedup={speedup:.2f}x")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="InProcessSDK Demo")
    parser.add_argument(
        "--mode",
        choices=["python", "cython", "c", "benchmark"],
        default="python",
    )
    parser.add_argument("--num-envs", type=int, default=4)
    parser.add_argument("--num-steps", type=int, default=2000)
    parser.add_argument(
        "--parallel",
        choices=["sequential", "thread", "subprocess"],
        default="sequential",
    )
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    dispatch = {
        "python": demo_python,
        "cython": demo_cython,
        "c": demo_c,
        "benchmark": demo_benchmark,
    }
    dispatch[args.mode](args)


if __name__ == "__main__":
    main()
