package simulations

import (
	"fmt"
	"log"

	"github.com/jelech/rl_env_engine/server"
)

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

// WithHost sets the host for HTTP server
func (c *HTTPServerConfig) WithHost(host string) *HTTPServerConfig {
	c.Host = host
	return c
}

// WithPort sets the port for HTTP server
func (c *HTTPServerConfig) WithPort(port int) *HTTPServerConfig {
	c.Port = port
	return c
}

// Address returns the full address string
func (c *HTTPServerConfig) Address() string {
	return fmt.Sprintf("%s:%d", c.Host, c.Port)
}
