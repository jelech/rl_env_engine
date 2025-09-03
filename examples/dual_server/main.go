package main

import (
	"log"

	simulations "github.com/jelech/rl_env_engine"
)

func main() {
	// 创建服务器配置
	config := &simulations.ServerConfig{
		HTTPConfig: simulations.NewHTTPServerConfig(8080).WithHost("0.0.0.0"),
		GrpcConfig: simulations.NewGrpcServerConfig(9090).WithHost("0.0.0.0"),
	}

	log.Println("Starting both HTTP and gRPC simulation servers...")
	log.Printf("HTTP server will listen on %s", config.HTTPConfig.Address())
	log.Printf("gRPC server will listen on %s", config.GrpcConfig.Address())

	log.Println("HTTP endpoints:")
	log.Println("  GET  /         - API information")
	log.Println("  GET  /info     - Environment information")
	log.Println("  POST /create   - Create environment")
	log.Println("  POST /reset    - Reset environment")
	log.Println("  POST /step     - Step environment")
	log.Println("  POST /close    - Close environment")

	log.Println("gRPC methods:")
	log.Println("  - GetInfo: Get service information")
	log.Println("  - CreateEnvironment: Create simulation environment")
	log.Println("  - ResetEnvironment: Reset environment")
	log.Println("  - StepEnvironment: Execute simulation step")
	log.Println("  - CloseEnvironment: Close environment")
	log.Println("  - StreamStep: Stream simulation steps")

	// 启动两个服务器并等待
	if err := simulations.StartServersAndWait(config); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
