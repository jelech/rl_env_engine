// Package sdk provides a flexible simulation framework for various scenarios.
// It supports reinforcement learning capabilities with extensible scenario support.
package sdk

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/jelech/rl_env_engine/go/internal/scenarios/simple"
	"github.com/jelech/rl_env_engine/go/internal/server"
	"github.com/jelech/rl_env_engine/go/pkg/core"
)

// Simulation represents the main simulation interface
type Simulation = core.Environment

// Config represents simulation configuration
type Config = core.Config

// Observation represents environment observation
type Observation = core.Observation

// Action represents agent action
type Action = core.Action

// NewSimulation creates a new simulation environment for the specified scenario
func NewSimulation(scenario string, config map[string]interface{}) (Simulation, error) {
	engine := core.NewSimulationEngine()

	// Register built-in scenarios
	registerBuiltinScenarios(engine)

	// Convert config map to Config interface
	cfg := core.NewBaseConfig(config)
	return engine.CreateEnvironment(scenario, cfg)
}

// NewSimpleSimulation creates a simple simulation with simplified configuration
func NewSimpleSimulation(opts ...SimpleOption) (Simulation, error) {
	config := &SimpleConfig{
		MaxSteps:  100,
		Tolerance: 0.1,
	}

	// Apply options
	for _, opt := range opts {
		opt(config)
	}

	configMap := map[string]interface{}{
		"max_steps": config.MaxSteps,
		"tolerance": config.Tolerance,
	}

	return NewSimulation("simple", configMap)
}

// SimpleConfig represents simple simulation configuration
type SimpleConfig struct {
	MaxSteps  int
	Tolerance float64
}

// SimpleOption is a function type for configuring simple simulation
type SimpleOption func(*SimpleConfig)

// WithMaxSteps sets the maximum steps for simple simulation
func WithMaxSteps(steps int) SimpleOption {
	return func(c *SimpleConfig) {
		c.MaxSteps = steps
	}
}

// WithTolerance sets the tolerance for simple simulation
func WithTolerance(tolerance float64) SimpleOption {
	return func(c *SimpleConfig) {
		c.Tolerance = tolerance
	}
}

// NewSimpleAction creates a new simple action
func NewSimpleAction(value float64) Action {
	return simple.NewSimpleAction(value)
}

// GetObservationData extracts float64 data from observation
func GetObservationData(obs Observation) []float64 {
	return obs.GetData()
}

// GetObservationMetadata extracts metadata from observation
func GetObservationMetadata(obs Observation) map[string]interface{} {
	return obs.GetMetadata()
}

// RunSimulation is a convenience function to run a complete simulation
func RunSimulation(scenario string, config map[string]interface{}, episodes int, actionFunc func([]Observation) []Action) error {
	sim, err := NewSimulation(scenario, config)
	if err != nil {
		return fmt.Errorf("failed to create simulation: %w", err)
	}
	defer sim.Close()

	ctx := context.Background()

	for episode := 0; episode < episodes; episode++ {
		// Reset environment
		observations, err := sim.Reset(ctx)
		if err != nil {
			return fmt.Errorf("failed to reset simulation at episode %d: %w", episode, err)
		}

		for step := 0; step < 100; step++ { // Max 100 steps per episode
			// Get actions from user function
			actions := actionFunc(observations)

			// Execute step
			obs, rewards, done, err := sim.Step(ctx, actions)
			if err != nil {
				return fmt.Errorf("failed to step simulation at episode %d, step %d: %w", episode, step, err)
			}

			observations = obs

			// Check if done
			if len(done) > 0 && done[0] {
				break
			}

			// Optional: use rewards for logging or early termination
			_ = rewards
		}
	}

	return nil
}

// registerBuiltinScenarios registers all built-in scenarios
func registerBuiltinScenarios(engine *core.SimulationEngine) {
	// Register simple test scenario
	simpleScenario := simple.NewSimpleScenario()
	engine.RegisterScenario(simpleScenario)
}

// ServerConfig represents configuration for both HTTP and gRPC servers
type ServerConfig struct {
	HTTPConfig *HTTPServerConfig
	GrpcConfig *GrpcServerConfig
}

// DefaultServerConfig returns default configuration for both servers
func DefaultServerConfig() *ServerConfig {
	return &ServerConfig{
		HTTPConfig: DefaultHTTPServerConfig(),
		GrpcConfig: DefaultGrpcServerConfig(),
	}
}

// StartServers starts both HTTP and gRPC servers concurrently
// Returns error channels for each server
func StartServers(config *ServerConfig) (<-chan error, <-chan error) {
	if config == nil {
		config = DefaultServerConfig()
	}

	var wg sync.WaitGroup
	httpErrCh := make(chan error, 1)
	grpcErrCh := make(chan error, 1)

	// Start HTTP server
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer close(httpErrCh)
		log.Printf("Starting HTTP server on %s", config.HTTPConfig.Address())
		if err := StartHTTPServer(config.HTTPConfig); err != nil {
			httpErrCh <- err
		}
	}()

	// Start gRPC server
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer close(grpcErrCh)
		log.Printf("Starting gRPC server on %s", config.GrpcConfig.Address())
		if err := StartGrpcServer(config.GrpcConfig); err != nil {
			grpcErrCh <- err
		}
	}()

	return httpErrCh, grpcErrCh
}

// StartServersAndWait starts both servers and waits for them to finish
// Returns the first error encountered from either server
func StartServersAndWait(config *ServerConfig) error {
	httpErrCh, grpcErrCh := StartServers(config)

	// Wait for the first error or completion
	select {
	case err := <-httpErrCh:
		if err != nil {
			return fmt.Errorf("HTTP server error: %w", err)
		}
	case err := <-grpcErrCh:
		if err != nil {
			return fmt.Errorf("gRPC server error: %w", err)
		}
	}

	return nil
}

// GrpcServerConfig represents gRPC server configuration
type GrpcServerConfig struct {
	Port int
	Host string
}

// DefaultGrpcServerConfig returns default gRPC server configuration
func DefaultGrpcServerConfig() *GrpcServerConfig {
	return &GrpcServerConfig{
		Port: 9090,
		Host: "localhost",
	}
}

// StartGrpcServer starts the gRPC API server for reinforcement learning integration
// This allows gRPC clients to interact with the simulation
func StartGrpcServer(config *GrpcServerConfig) error {
	if config == nil {
		config = DefaultGrpcServerConfig()
	}

	grpcServer := server.NewGrpcServer()

	log.Printf("Starting Simulation gRPC server...")
	log.Printf("Server will be available at %s:%d", config.Host, config.Port)
	log.Printf("gRPC clients can connect to this server for RL training")

	return grpcServer.StartGrpcServer(config.Port)
}

// StartGrpcServerAsync starts the gRPC server in a separate goroutine
// Returns a channel that will receive any error from the server
func StartGrpcServerAsync(config *GrpcServerConfig) <-chan error {
	errCh := make(chan error, 1)

	go func() {
		defer close(errCh)
		if err := StartGrpcServer(config); err != nil {
			errCh <- err
		}
	}()

	return errCh
}

// NewGrpcServerConfig creates a new gRPC server configuration
func NewGrpcServerConfig(port int) *GrpcServerConfig {
	return &GrpcServerConfig{
		Port: port,
		Host: "localhost",
	}
}

// WithHost sets the host for gRPC server
func (c *GrpcServerConfig) WithHost(host string) *GrpcServerConfig {
	c.Host = host
	return c
}

// WithPort sets the port for gRPC server
func (c *GrpcServerConfig) WithPort(port int) *GrpcServerConfig {
	c.Port = port
	return c
}

// Address returns the full address string
func (c *GrpcServerConfig) Address() string {
	return fmt.Sprintf("%s:%d", c.Host, c.Port)
}

// HTTPServerConfig represents HTTP server configuration
type HTTPServerConfig struct {
	Port int
	Host string
}

// DefaultHTTPServerConfig returns default HTTP server configuration
func DefaultHTTPServerConfig() *HTTPServerConfig {
	return &HTTPServerConfig{
		Port: 8080,
		Host: "localhost",
	}
}

// StartHTTPServer starts the HTTP API server for reinforcement learning integration
// This allows Python clients and other HTTP clients to interact with the simulation
func StartHTTPServer(config *HTTPServerConfig) error {
	if config == nil {
		config = DefaultHTTPServerConfig()
	}

	api := server.NewGymAPI()

	log.Printf("Starting Simulation HTTP API server...")
	log.Printf("Server will be available at http://%s:%d", config.Host, config.Port)
	log.Printf("Python clients can connect to this server for RL training")

	return api.StartServer(config.Port)
}

// StartHTTPServerAsync starts the HTTP server in a separate goroutine
// Returns a channel that will receive any error from the server
func StartHTTPServerAsync(config *HTTPServerConfig) <-chan error {
	errCh := make(chan error, 1)

	go func() {
		defer close(errCh)
		if err := StartHTTPServer(config); err != nil {
			errCh <- err
		}
	}()

	return errCh
}

// NewHTTPServerConfig creates a new HTTP server configuration
func NewHTTPServerConfig(port int) *HTTPServerConfig {
	return &HTTPServerConfig{
		Port: port,
		Host: "localhost",
	}
}

// WithHTTPHost sets the host for HTTP server
func (c *HTTPServerConfig) WithHost(host string) *HTTPServerConfig {
	c.Host = host
	return c
}

// WithHTTPPort sets the port for HTTP server
func (c *HTTPServerConfig) WithPort(port int) *HTTPServerConfig {
	c.Port = port
	return c
}

// HTTPAddress returns the full address string
func (c *HTTPServerConfig) Address() string {
	return fmt.Sprintf("%s:%d", c.Host, c.Port)
}
