package main

import (
	"context"
	"log"
	"time"

	pb "github.com/jelech/rl_env_engine/proto"
	"google.golang.org/grpc"
)

func main() {
	// 连接到gRPC服务器
	conn, err := grpc.Dial("127.0.0.1:9090", grpc.WithInsecure())
	if err != nil {
		log.Fatalf("Failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewSimulationServiceClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// 测试GetInfo
	log.Println("Testing GetInfo...")
	info, err := client.GetInfo(ctx, &pb.GetInfoRequest{})
	if err != nil {
		log.Printf("GetInfo failed: %v", err)
	} else {
		log.Printf("Service: %s, Version: %s", info.Name, info.Version)
		log.Printf("Available scenarios: %v", info.Scenarios)
	}

	// 测试CreateEnvironment - 使用简单场景
	log.Println("Testing CreateEnvironment with simple scenario...")
	envID := "test_simple_env"
	createResp, err := client.CreateEnvironment(ctx, &pb.CreateEnvironmentRequest{
		EnvId:    envID,
		Scenario: "simple",
		Config: map[string]string{
			"max_steps": "50",
			"tolerance": "0.5",
		},
	})
	if err != nil {
		log.Printf("CreateEnvironment failed: %v", err)
		return
	}

	if !createResp.Success {
		log.Printf("CreateEnvironment unsuccessful: %s", createResp.Message)
		return
	}

	log.Printf("Environment created successfully: %s", createResp.Message)

	// 测试ResetEnvironment - 这是导致panic的地方
	log.Println("Testing ResetEnvironment...")
	resetResp, err := client.ResetEnvironment(ctx, &pb.ResetEnvironmentRequest{
		EnvId: envID,
	})
	if err != nil {
		log.Printf("ResetEnvironment failed: %v", err)
	} else {
		log.Printf("Environment reset successfully, observations count: %d", len(resetResp.Observations))
		if len(resetResp.Observations) > 0 {
			log.Printf("First observation data length: %d", len(resetResp.Observations[0].Data))
		}
	}

	// 测试StepEnvironment - 使用简单action
	log.Println("Testing StepEnvironment with simple action...")
	action := &pb.Action{
		Data: &pb.Action_FloatValue{
			FloatValue: 1.5,
		},
	}

	stepResp, err := client.StepEnvironment(ctx, &pb.StepEnvironmentRequest{
		EnvId:   envID,
		Actions: []*pb.Action{action},
	})
	if err != nil {
		log.Printf("StepEnvironment failed: %v", err)
	} else {
		log.Printf("Step successful, observations: %d, rewards: %v, done: %v",
			len(stepResp.Observations), stepResp.Rewards, stepResp.Done)
	}

	// 测试CloseEnvironment
	log.Println("Testing CloseEnvironment...")
	closeResp, err := client.CloseEnvironment(ctx, &pb.CloseEnvironmentRequest{
		EnvId: envID,
	})
	if err != nil {
		log.Printf("CloseEnvironment failed: %v", err)
	} else {
		log.Printf("Environment closed: %s", closeResp.Message)
	}

	log.Println("All tests completed!")
}
