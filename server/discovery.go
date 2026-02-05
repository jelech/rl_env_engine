package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/redis/go-redis/v9"
)

const (
	DiscoveryKey = "simulation:services"
	TTL          = 10 * time.Second
)

type ServiceMetadata struct {
	Addr      string   `json:"addr"`
	Scenarios []string `json:"scenarios"`
	Lang      string   `json:"lang"`
	Encodings []string `json:"encodings"`
}

type ServiceRegistry struct {
	client *redis.Client
	meta   ServiceMetadata
	stop   chan struct{}
}

func NewServiceRegistry(redisURL string, meta ServiceMetadata) (*ServiceRegistry, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, err
	}

	client := redis.NewClient(opts)
	return &ServiceRegistry{
		client: client,
		meta:   meta,
		stop:   make(chan struct{}),
	}, nil
}

func (r *ServiceRegistry) Start() {
	go func() {
		ticker := time.NewTicker(TTL / 2)
		defer ticker.Stop()

		// Initial registration
		if err := r.register(); err != nil {
			log.Printf("Failed to register service: %v", err)
		}

		for {
			select {
			case <-ticker.C:
				if err := r.register(); err != nil {
					log.Printf("Failed to refresh service registration: %v", err)
				}
			case <-r.stop:
				r.deregister()
				return
			}
		}
	}()
}

func (r *ServiceRegistry) Stop() {
	close(r.stop)
}

func (r *ServiceRegistry) register() error {
	ctx := context.Background()
	
	// Serialize metadata
	data, err := json.Marshal(r.meta)
	if err != nil {
		return err
	}

	// Use ZAdd to maintain a list of active services with timestamps
	// The member is the JSON metadata (which includes the address)
	// This allows the client to get all info in one go
	// Note: In a real production system, we might want to separate the heartbeat (timestamp) 
	// from the metadata to avoid re-sending JSON every few seconds, but for this scale it's fine.
	// Actually, the previous python implementation used ZADD with addr as member.
	// To be compatible but richer, let's use the JSON string as the member.
	
	return r.client.ZAdd(ctx, DiscoveryKey, redis.Z{
		Score:  float64(time.Now().Unix() + int64(TTL.Seconds())),
		Member: string(data),
	}).Err()
}

func (r *ServiceRegistry) deregister() {
	ctx := context.Background()
	data, _ := json.Marshal(r.meta)
	r.client.ZRem(ctx, DiscoveryKey, string(data))
}

// Helper to get advertised address
func GetAdvertisedAddr(port int) string {
	ip := os.Getenv("ADVERTISED_IP")
	if ip == "" {
		ip = "127.0.0.1" // Fallback
	}
	
	advPort := os.Getenv("ADVERTISED_PORT")
	if advPort == "" {
		advPort = fmt.Sprintf("%d", port)
	}
	
	return fmt.Sprintf("%s:%s", ip, advPort)
}
