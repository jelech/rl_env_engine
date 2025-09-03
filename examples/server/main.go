// Example showing how to start an HTTP server for RL integration
package main

import (
	"flag"
	"log"

	simulations "github.com/jelech/rl_env_engine"
)

func main() {
	// Parse command line flags
	port := flag.Int("port", 8080, "Port to run the server on")
	host := flag.String("host", "localhost", "Host to bind the server to")
	flag.Parse()

	// Create server configuration
	config := simulations.NewHTTPServerConfig(*port).WithHost(*host)

	log.Printf("Starting simulation HTTP server on %s", config.Address())
	log.Println("This server provides OpenAI Gym-compatible API for:")
	log.Println("  - Python reinforcement learning libraries")
	log.Println("  - HTTP-based simulation clients")
	log.Println("  - Remote simulation execution")
	log.Println()
	log.Println("Available endpoints:")
	log.Println("  GET  /         - API information")
	log.Println("  GET  /info     - Environment information")
	log.Println("  POST /create   - Create environment")
	log.Println("  POST /reset    - Reset environment")
	log.Println("  POST /step     - Step environment")
	log.Println("  POST /close    - Close environment")
	log.Println()
	log.Println("Use Ctrl+C to stop the server")

	// Start the server (blocking call)
	if err := simulations.StartHTTPServer(config); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
