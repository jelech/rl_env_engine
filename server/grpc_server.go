package server

import (
	"context"
	"fmt"
	"log"
	"net"

	"github.com/jelech/rl_env_engine/core"
	pb "github.com/jelech/rl_env_engine/proto"
	"github.com/jelech/rl_env_engine/scenarios/simple"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

// GrpcServer implements the gRPC simulation service
type GrpcServer struct {
	pb.UnimplementedSimulationServiceServer
	engine       *core.SimulationEngine
	environments map[string]core.Environment
	configs      map[string]core.Config
}

// NewGrpcServer creates a new gRPC server instance
func NewGrpcServer() *GrpcServer {
	engine := core.NewSimulationEngine()

	// 注册简单测试场景
	simpleScenario := simple.NewSimpleScenario()
	engine.RegisterScenario(simpleScenario)

	return &GrpcServer{
		engine:       engine,
		environments: make(map[string]core.Environment),
		configs:      make(map[string]core.Config),
	}
}

// StartGrpcServer starts the gRPC server on the specified port
func (s *GrpcServer) StartGrpcServer(port int) error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return fmt.Errorf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterSimulationServiceServer(grpcServer, s)

	// Enable reflection for debugging
	reflection.Register(grpcServer)

	log.Printf("Starting gRPC Simulation server on port %d", port)
	log.Printf("gRPC endpoints available:")
	log.Printf("  GetInfo - Get service information")
	log.Printf("  CreateEnvironment - Create a new environment")
	log.Printf("  ResetEnvironment - Reset an environment")
	log.Printf("  StepEnvironment - Execute one simulation step")
	log.Printf("  CloseEnvironment - Close an environment")
	log.Printf("  StreamStep - Stream simulation steps")

	return grpcServer.Serve(lis)
}

// GetInfo returns information about the simulation service
func (s *GrpcServer) GetInfo(ctx context.Context, req *pb.GetInfoRequest) (*pb.GetInfoResponse, error) {
	scenarios := s.engine.ListScenarios()
	envIDs := make([]string, 0, len(s.environments))
	for envID := range s.environments {
		envIDs = append(envIDs, envID)
	}

	info := map[string]string{
		"total_scenarios":     fmt.Sprintf("%d", len(scenarios)),
		"active_environments": fmt.Sprintf("%d", len(envIDs)),
		"server_type":         "gRPC",
	}

	return &pb.GetInfoResponse{
		Scenarios: scenarios,
		EnvIds:    envIDs,
		Info:      info,
		Version:   "1.0.0",
		Name:      "Simulation gRPC Service",
	}, nil
}

// CreateEnvironment creates a new simulation environment
func (s *GrpcServer) CreateEnvironment(ctx context.Context, req *pb.CreateEnvironmentRequest) (*pb.CreateEnvironmentResponse, error) {
	// 检查环境是否已存在
	if _, exists := s.environments[req.EnvId]; exists {
		return &pb.CreateEnvironmentResponse{
			Success: false,
			Message: fmt.Sprintf("Environment %s already exists", req.EnvId),
		}, nil
	}

	// 创建配置
	config := core.NewBaseConfig()
	for key, value := range req.Config {
		config.SetValue(key, value)
	}

	// 创建环境
	env, err := s.engine.CreateEnvironment(req.Scenario, config)
	if err != nil {
		return &pb.CreateEnvironmentResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to create environment: %v", err),
		}, nil
	}

	// 保存环境和配置
	s.environments[req.EnvId] = env
	s.configs[req.EnvId] = config

	return &pb.CreateEnvironmentResponse{
		Success: true,
		Message: fmt.Sprintf("Environment %s created successfully", req.EnvId),
	}, nil
}

// ResetEnvironment resets an existing environment
func (s *GrpcServer) ResetEnvironment(ctx context.Context, req *pb.ResetEnvironmentRequest) (*pb.ResetEnvironmentResponse, error) {
	env, exists := s.environments[req.EnvId]
	if !exists {
		return nil, fmt.Errorf("environment %s not found", req.EnvId)
	}

	observations, err := env.Reset(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to reset environment: %v", err)
	}

	// 转换观察为protobuf格式
	protoObservations := make([]*pb.Observation, len(observations))
	for i, obs := range observations {
		metadata := make(map[string]string)
		for k, v := range obs.GetMetadata() {
			metadata[k] = fmt.Sprintf("%v", v)
		}

		protoObservations[i] = &pb.Observation{
			Data:     obs.GetData(),
			Metadata: metadata,
		}
	}

	info := make(map[string]string)
	for k, v := range env.GetInfo() {
		info[k] = fmt.Sprintf("%v", v)
	}

	return &pb.ResetEnvironmentResponse{
		Observations: protoObservations,
		Info:         info,
	}, nil
}

// StepEnvironment executes one step in the simulation
func (s *GrpcServer) StepEnvironment(ctx context.Context, req *pb.StepEnvironmentRequest) (*pb.StepEnvironmentResponse, error) {
	env, exists := s.environments[req.EnvId]
	if !exists {
		return nil, fmt.Errorf("environment %s not found", req.EnvId)
	}

	// 转换action从protobuf格式
	actions, err := s.convertProtoAction(req.Action)
	if err != nil {
		return nil, fmt.Errorf("failed to convert action: %v", err)
	}

	observations, rewards, done, err := env.Step(ctx, actions)
	if err != nil {
		return nil, fmt.Errorf("failed to step environment: %v", err)
	}

	// 转换观察为protobuf格式
	protoObservations := make([]*pb.Observation, len(observations))
	for i, obs := range observations {
		metadata := make(map[string]string)
		for k, v := range obs.GetMetadata() {
			metadata[k] = fmt.Sprintf("%v", v)
		}

		protoObservations[i] = &pb.Observation{
			Data:     obs.GetData(),
			Metadata: metadata,
		}
	}

	info := make(map[string]string)
	for k, v := range env.GetInfo() {
		info[k] = fmt.Sprintf("%v", v)
	}

	return &pb.StepEnvironmentResponse{
		Observations: protoObservations,
		Rewards:      rewards,
		Done:         done,
		Info:         info,
	}, nil
}

// CloseEnvironment closes an existing environment
func (s *GrpcServer) CloseEnvironment(ctx context.Context, req *pb.CloseEnvironmentRequest) (*pb.CloseEnvironmentResponse, error) {
	env, exists := s.environments[req.EnvId]
	if !exists {
		return nil, fmt.Errorf("environment %s not found", req.EnvId)
	}

	if err := env.Close(); err != nil {
		return &pb.CloseEnvironmentResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to close environment: %v", err),
		}, nil
	}

	delete(s.environments, req.EnvId)
	delete(s.configs, req.EnvId)

	return &pb.CloseEnvironmentResponse{
		Success: true,
		Message: fmt.Sprintf("Environment %s closed successfully", req.EnvId),
	}, nil
}

// StreamStep implements streaming simulation steps
func (s *GrpcServer) StreamStep(stream pb.SimulationService_StreamStepServer) error {
	for {
		req, err := stream.Recv()
		if err != nil {
			return err
		}

		// 处理步进请求
		resp, err := s.StepEnvironment(stream.Context(), req)
		if err != nil {
			return err
		}

		// 发送响应
		if err := stream.Send(resp); err != nil {
			return err
		}
	}
}

// convertProtoAction converts protobuf Action to core.Action
func (s *GrpcServer) convertProtoAction(protoAction *pb.Action) ([]core.Action, error) {
	if protoAction == nil {
		return nil, fmt.Errorf("action is nil")
	}

	switch actionType := protoAction.ActionType.(type) {
	case *pb.Action_SimpleAction:
		// 验证SimpleAction不为nil
		if actionType.SimpleAction == nil {
			return nil, fmt.Errorf("simple action is nil")
		}

		// 转换简单action
		action := simple.NewSimpleAction(actionType.SimpleAction.Value)
		if action == nil {
			return nil, fmt.Errorf("failed to create simple action")
		}

		return []core.Action{action}, nil

	case nil:
		return nil, fmt.Errorf("action type is nil")
	default:
		return nil, fmt.Errorf("unsupported action type: %T", actionType)
	}
}
