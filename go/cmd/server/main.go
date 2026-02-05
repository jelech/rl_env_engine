package main

import (
	"log"

	"github.com/jelech/rl_env_engine/go/pkg/sdk"
)

func main() {
	// 创建gRPC服务器配置
	grpcConfig := sdk.NewGrpcServerConfig(9090).WithHost("0.0.0.0")

	log.Println("Starting gRPC simulation server...")
	log.Printf("gRPC server will listen on %s", grpcConfig.Address())
	log.Println("Available gRPC methods:")
	log.Println("  - GetInfo: Get service information")
	log.Println("  - CreateEnvironment: Create simulation environment")
	log.Println("  - ResetEnvironment: Reset environment")
	log.Println("  - StepEnvironment: Execute simulation step")
	log.Println("  - CloseEnvironment: Close environment")
	log.Println("  - StreamStep: Stream simulation steps")

	// 启动gRPC服务器
	if err := sdk.StartGrpcServer(grpcConfig); err != nil {
		log.Fatalf("Failed to start gRPC server: %v", err)
	}
}
