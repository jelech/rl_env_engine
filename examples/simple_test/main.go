package main

import (
	"context"
	"log"

	simulations "github.com/jelech/rl_env_engine"
)

func main() {
	log.Println("Simple Simulation Example")
	log.Println("=========================")

	// 创建简单仿真环境
	sim, err := simulations.NewSimpleSimulation(
		simulations.WithMaxSteps(20),
		simulations.WithTolerance(0.5),
	)
	if err != nil {
		log.Fatalf("Failed to create simulation: %v", err)
	}
	defer sim.Close()

	ctx := context.Background()

	// 运行几个episode
	for episode := 0; episode < 3; episode++ {
		log.Printf("\n--- Episode %d ---", episode+1)

		// 重置环境
		observations, err := sim.Reset(ctx)
		if err != nil {
			log.Fatalf("Failed to reset simulation: %v", err)
		}

		log.Printf("Initial observation: %v", simulations.GetObservationData(observations[0]))
		metadata := simulations.GetObservationMetadata(observations[0])
		log.Printf("Target value: %v", metadata["target_value"])

		// 运行仿真步骤
		for step := 0; step < 20; step++ {
			// 获取当前状态
			obsData := simulations.GetObservationData(observations[0])
			currentValue := obsData[0] // 当前值
			targetValue := obsData[1]  // 目标值
			difference := obsData[2]   // 差值

			// 简单策略：朝目标方向移动
			actionValue := 0.0
			if difference > 0 {
				actionValue = 0.8 // 正向移动
			} else if difference < 0 {
				actionValue = -0.8 // 负向移动
			}

			// 创建action
			action := simulations.NewSimpleAction(actionValue)
			actions := []simulations.Action{action}

			// 执行步骤
			obs, rewards, done, err := sim.Step(ctx, actions)
			if err != nil {
				log.Printf("Step %d failed: %v", step+1, err)
				break
			}

			observations = obs
			newObsData := simulations.GetObservationData(observations[0])
			newCurrentValue := newObsData[0]
			newDifference := newObsData[2]

			log.Printf("Step %d: action=%.2f, current=%.2f->%.2f, target=%.2f, diff=%.2f, reward=%.2f, done=%v",
				step+1, actionValue, currentValue, newCurrentValue, targetValue, newDifference, rewards[0], done[0])

			// 检查是否完成
			if len(done) > 0 && done[0] {
				log.Printf("Episode completed after %d steps!", step+1)
				break
			}
		}
	}

	log.Println("\nSimulation completed!")
}
