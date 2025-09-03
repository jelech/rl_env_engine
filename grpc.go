package rl_env_engine

import (
	"fmt"
	"log"

	"github.com/jelech/rl_env_engine/server"
)

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
