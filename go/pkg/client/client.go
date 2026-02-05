// Package client provides a Go client SDK for connecting to RL Env Engine servers.
package client

import (
	"context"
	"fmt"
	"time"

	pb "github.com/jelech/rl_env_engine/go/pkg/api/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/protobuf/types/known/structpb"
)

// Client represents a gRPC client for the simulation service
type Client struct {
	conn   *grpc.ClientConn
	client pb.SimulationServiceClient
	addr   string
}

// ClientOption is a function type for configuring the client
type ClientOption func(*clientConfig)

type clientConfig struct {
	timeout time.Duration
}

// WithTimeout sets the connection timeout
func WithTimeout(timeout time.Duration) ClientOption {
	return func(c *clientConfig) {
		c.timeout = timeout
	}
}

// NewClient creates a new simulation client
func NewClient(addr string, opts ...ClientOption) (*Client, error) {
	cfg := &clientConfig{
		timeout: 10 * time.Second,
	}

	for _, opt := range opts {
		opt(cfg)
	}

	ctx, cancel := context.WithTimeout(context.Background(), cfg.timeout)
	defer cancel()

	conn, err := grpc.DialContext(ctx, addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to %s: %w", addr, err)
	}

	return &Client{
		conn:   conn,
		client: pb.NewSimulationServiceClient(conn),
		addr:   addr,
	}, nil
}

// Close closes the client connection
func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// GetInfo retrieves information about the simulation service
func (c *Client) GetInfo(ctx context.Context) (*InfoResponse, error) {
	resp, err := c.client.GetInfo(ctx, &pb.GetInfoRequest{})
	if err != nil {
		return nil, fmt.Errorf("failed to get info: %w", err)
	}

	info := make(map[string]interface{})
	if resp.Info != nil {
		info = resp.Info.AsMap()
	}

	return &InfoResponse{
		Scenarios: resp.Scenarios,
		EnvIDs:    resp.EnvIds,
		Info:      info,
		Version:   resp.Version,
		Name:      resp.Name,
	}, nil
}

// CreateEnvironment creates a new simulation environment
func (c *Client) CreateEnvironment(ctx context.Context, envID, scenario string, config map[string]interface{}) error {
	configStruct, err := structpb.NewStruct(config)
	if err != nil {
		return fmt.Errorf("failed to create config struct: %w", err)
	}

	resp, err := c.client.CreateEnvironment(ctx, &pb.CreateEnvironmentRequest{
		EnvId:    envID,
		Scenario: scenario,
		Config:   configStruct,
	})
	if err != nil {
		return fmt.Errorf("failed to create environment: %w", err)
	}

	if !resp.Success {
		return fmt.Errorf("failed to create environment: %s", resp.Message)
	}

	return nil
}

// ResetEnvironment resets an existing environment
func (c *Client) ResetEnvironment(ctx context.Context, envID string) (*ResetResponse, error) {
	resp, err := c.client.ResetEnvironment(ctx, &pb.ResetEnvironmentRequest{
		EnvId: envID,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to reset environment: %w", err)
	}

	observations := make([]Observation, len(resp.Observations))
	for i, obs := range resp.Observations {
		metadata := make(map[string]interface{})
		if obs.Metadata != nil {
			metadata = obs.Metadata.AsMap()
		}
		observations[i] = Observation{
			Data:     obs.Data,
			Metadata: metadata,
		}
	}

	info := make(map[string]interface{})
	if resp.Info != nil {
		info = resp.Info.AsMap()
	}

	return &ResetResponse{
		Observations: observations,
		Info:         info,
	}, nil
}

// StepEnvironment executes one step in the simulation
func (c *Client) StepEnvironment(ctx context.Context, envID string, actions []Action) (*StepResponse, error) {
	protoActions := make([]*pb.Action, len(actions))
	for i, action := range actions {
		protoActions[i] = action.ToProto()
	}

	resp, err := c.client.StepEnvironment(ctx, &pb.StepEnvironmentRequest{
		EnvId:   envID,
		Actions: protoActions,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to step environment: %w", err)
	}

	observations := make([]Observation, len(resp.Observations))
	for i, obs := range resp.Observations {
		metadata := make(map[string]interface{})
		if obs.Metadata != nil {
			metadata = obs.Metadata.AsMap()
		}
		observations[i] = Observation{
			Data:     obs.Data,
			Metadata: metadata,
		}
	}

	info := make(map[string]interface{})
	if resp.Info != nil {
		info = resp.Info.AsMap()
	}

	return &StepResponse{
		Observations: observations,
		Rewards:      resp.Rewards,
		Done:         resp.Done,
		Info:         info,
	}, nil
}

// CloseEnvironment closes an existing environment
func (c *Client) CloseEnvironment(ctx context.Context, envID string) error {
	resp, err := c.client.CloseEnvironment(ctx, &pb.CloseEnvironmentRequest{
		EnvId: envID,
	})
	if err != nil {
		return fmt.Errorf("failed to close environment: %w", err)
	}

	if !resp.Success {
		return fmt.Errorf("failed to close environment: %s", resp.Message)
	}

	return nil
}

// GetSpaces retrieves the action and observation space definitions
func (c *Client) GetSpaces(ctx context.Context, envID string) (*SpacesResponse, error) {
	resp, err := c.client.GetSpaces(ctx, &pb.GetSpacesRequest{
		EnvId: envID,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to get spaces: %w", err)
	}

	var actionSpace *ActionSpace
	if resp.ActionSpace != nil {
		actionSpace = &ActionSpace{
			Type:           SpaceType(resp.ActionSpace.Type),
			Low:            resp.ActionSpace.Low,
			High:           resp.ActionSpace.High,
			Shape:          resp.ActionSpace.Shape,
			Dtype:          resp.ActionSpace.Dtype,
			DiscreteValues: resp.ActionSpace.DiscreteValues,
		}
	}

	var observationSpace *ObservationSpace
	if resp.ObservationSpace != nil {
		observationSpace = &ObservationSpace{
			Type:  SpaceType(resp.ObservationSpace.Type),
			Low:   resp.ObservationSpace.Low,
			High:  resp.ObservationSpace.High,
			Shape: resp.ObservationSpace.Shape,
			Dtype: resp.ObservationSpace.Dtype,
		}
	}

	return &SpacesResponse{
		ActionSpace:      actionSpace,
		ObservationSpace: observationSpace,
	}, nil
}

// Response types

// InfoResponse represents the response from GetInfo
type InfoResponse struct {
	Scenarios []string
	EnvIDs    []string
	Info      map[string]interface{}
	Version   string
	Name      string
}

// ResetResponse represents the response from ResetEnvironment
type ResetResponse struct {
	Observations []Observation
	Info         map[string]interface{}
}

// StepResponse represents the response from StepEnvironment
type StepResponse struct {
	Observations []Observation
	Rewards      []float64
	Done         []bool
	Info         map[string]interface{}
}

// SpacesResponse represents the response from GetSpaces
type SpacesResponse struct {
	ActionSpace      *ActionSpace
	ObservationSpace *ObservationSpace
}

// Observation represents an observation from the environment
type Observation struct {
	Data     []float64
	Metadata map[string]interface{}
}

// Action represents an action to be sent to the environment
type Action struct {
	FloatValue  *float64
	IntValue    *int64
	BoolValue   *bool
	StringValue *string
	FloatArray  []float64
	IntArray    []int64
	BoolArray   []bool
}

// NewFloatAction creates an action with a float value
func NewFloatAction(value float64) Action {
	return Action{FloatValue: &value}
}

// NewIntAction creates an action with an int value
func NewIntAction(value int64) Action {
	return Action{IntValue: &value}
}

// NewBoolAction creates an action with a bool value
func NewBoolAction(value bool) Action {
	return Action{BoolValue: &value}
}

// NewFloatArrayAction creates an action with a float array
func NewFloatArrayAction(values []float64) Action {
	return Action{FloatArray: values}
}

// ToProto converts the action to a protobuf Action
func (a Action) ToProto() *pb.Action {
	if a.FloatValue != nil {
		return &pb.Action{Data: &pb.Action_FloatValue{FloatValue: *a.FloatValue}}
	}
	if a.IntValue != nil {
		return &pb.Action{Data: &pb.Action_IntValue{IntValue: *a.IntValue}}
	}
	if a.BoolValue != nil {
		return &pb.Action{Data: &pb.Action_BoolValue{BoolValue: *a.BoolValue}}
	}
	if a.StringValue != nil {
		return &pb.Action{Data: &pb.Action_StringValue{StringValue: *a.StringValue}}
	}
	if len(a.FloatArray) > 0 {
		return &pb.Action{Data: &pb.Action_FloatArray{FloatArray: &pb.FloatArray{Values: a.FloatArray}}}
	}
	if len(a.IntArray) > 0 {
		return &pb.Action{Data: &pb.Action_IntArray{IntArray: &pb.IntArray{Values: a.IntArray}}}
	}
	if len(a.BoolArray) > 0 {
		return &pb.Action{Data: &pb.Action_BoolArray{BoolArray: &pb.BoolArray{Values: a.BoolArray}}}
	}
	return &pb.Action{}
}

// SpaceType represents the type of space
type SpaceType int32

const (
	SpaceTypeBox           SpaceType = 0
	SpaceTypeDiscrete      SpaceType = 1
	SpaceTypeMultiDiscrete SpaceType = 2
	SpaceTypeMultiBinary   SpaceType = 3
	SpaceTypeDiscreteFloat SpaceType = 4
)

// ActionSpace represents the action space definition
type ActionSpace struct {
	Type           SpaceType
	Low            []float64
	High           []float64
	Shape          []int32
	Dtype          string
	DiscreteValues []float64
}

// ObservationSpace represents the observation space definition
type ObservationSpace struct {
	Type  SpaceType
	Low   []float64
	High  []float64
	Shape []int32
	Dtype string
}
