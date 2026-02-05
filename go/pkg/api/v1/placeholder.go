// Package v1 contains the generated protobuf code for the simulation service.
// Run `make proto` to generate the actual code from api/proto/v1/simulation.proto
//
// This placeholder file allows the Go module to build before proto generation.
// After running proto generation, DELETE this file - it will be superseded by:
//   - simulation.pb.go
//   - simulation_grpc.pb.go
package v1

import (
	"context"

	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/structpb"
)

// Placeholder types - these will be replaced by generated code

type GetInfoRequest struct{}
type GetInfoResponse struct {
	Scenarios []string
	EnvIds    []string
	Info      *structpb.Struct
	Version   string
	Name      string
}

type CreateEnvironmentRequest struct {
	EnvId    string
	Scenario string
	Config   *structpb.Struct
}

func (r *CreateEnvironmentRequest) GetConfig() *structpb.Struct { return r.Config }

type CreateEnvironmentResponse struct {
	Success bool
	Message string
}

type ResetEnvironmentRequest struct {
	EnvId string
}
type ResetEnvironmentResponse struct {
	Observations []*Observation
	Info         *structpb.Struct
}

type StepEnvironmentRequest struct {
	EnvId   string
	Actions []*Action
}
type StepEnvironmentResponse struct {
	Observations []*Observation
	Rewards      []float64
	Done         []bool
	Info         *structpb.Struct
}

type CloseEnvironmentRequest struct {
	EnvId string
}
type CloseEnvironmentResponse struct {
	Success bool
	Message string
}

type GetSpacesRequest struct {
	EnvId string
}
type GetSpacesResponse struct {
	ActionSpace      *ActionSpace
	ObservationSpace *ObservationSpace
}

type Observation struct {
	Data     []float64
	Metadata *structpb.Struct
}

type Action struct {
	Data isAction_Data
}

type isAction_Data interface {
	isAction_Data()
}

type Action_FloatValue struct{ FloatValue float64 }
type Action_IntValue struct{ IntValue int64 }
type Action_BoolValue struct{ BoolValue bool }
type Action_StringValue struct{ StringValue string }
type Action_FloatArray struct{ FloatArray *FloatArray }
type Action_IntArray struct{ IntArray *IntArray }
type Action_BoolArray struct{ BoolArray *BoolArray }
type Action_RawData struct{ RawData []byte }

func (*Action_FloatValue) isAction_Data()  {}
func (*Action_IntValue) isAction_Data()    {}
func (*Action_BoolValue) isAction_Data()   {}
func (*Action_StringValue) isAction_Data() {}
func (*Action_FloatArray) isAction_Data()  {}
func (*Action_IntArray) isAction_Data()    {}
func (*Action_BoolArray) isAction_Data()   {}
func (*Action_RawData) isAction_Data()     {}

func (a *Action) GetData() isAction_Data { return a.Data }

type FloatArray struct {
	Values []float64
}
type IntArray struct {
	Values []int64
}
type BoolArray struct {
	Values []bool
}

type SpaceType int32

const (
	SpaceType_BOX            SpaceType = 0
	SpaceType_DISCRETE       SpaceType = 1
	SpaceType_MULTI_DISCRETE SpaceType = 2
	SpaceType_MULTI_BINARY   SpaceType = 3
	SpaceType_DISCRETE_FLOAT SpaceType = 4
)

type ActionSpace struct {
	Type           SpaceType
	Low            []float64
	High           []float64
	Shape          []int32
	Dtype          string
	DiscreteValues []float64
}

type ObservationSpace struct {
	Type  SpaceType
	Low   []float64
	High  []float64
	Shape []int32
	Dtype string
}

// UnimplementedSimulationServiceServer must be embedded to have forward compatible implementations.
type UnimplementedSimulationServiceServer struct{}

func (UnimplementedSimulationServiceServer) GetInfo(context.Context, *GetInfoRequest) (*GetInfoResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) CreateEnvironment(context.Context, *CreateEnvironmentRequest) (*CreateEnvironmentResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) ResetEnvironment(context.Context, *ResetEnvironmentRequest) (*ResetEnvironmentResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) StepEnvironment(context.Context, *StepEnvironmentRequest) (*StepEnvironmentResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) CloseEnvironment(context.Context, *CloseEnvironmentRequest) (*CloseEnvironmentResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) GetSpaces(context.Context, *GetSpacesRequest) (*GetSpacesResponse, error) {
	return nil, nil
}
func (UnimplementedSimulationServiceServer) StreamStep(SimulationService_StreamStepServer) error {
	return nil
}

// SimulationServiceServer is the server API for SimulationService service.
type SimulationServiceServer interface {
	GetInfo(context.Context, *GetInfoRequest) (*GetInfoResponse, error)
	CreateEnvironment(context.Context, *CreateEnvironmentRequest) (*CreateEnvironmentResponse, error)
	ResetEnvironment(context.Context, *ResetEnvironmentRequest) (*ResetEnvironmentResponse, error)
	StepEnvironment(context.Context, *StepEnvironmentRequest) (*StepEnvironmentResponse, error)
	CloseEnvironment(context.Context, *CloseEnvironmentRequest) (*CloseEnvironmentResponse, error)
	GetSpaces(context.Context, *GetSpacesRequest) (*GetSpacesResponse, error)
	StreamStep(SimulationService_StreamStepServer) error
}

// SimulationService_StreamStepServer is the server stream for StreamStep
type SimulationService_StreamStepServer interface {
	Send(*StepEnvironmentResponse) error
	Recv() (*StepEnvironmentRequest, error)
	grpc.ServerStream
}

// RegisterSimulationServiceServer registers the server
func RegisterSimulationServiceServer(s grpc.ServiceRegistrar, srv SimulationServiceServer) {
	// Placeholder - actual implementation in generated code
}

// SimulationServiceClient is the client API for SimulationService service.
type SimulationServiceClient interface {
	GetInfo(ctx context.Context, in *GetInfoRequest, opts ...grpc.CallOption) (*GetInfoResponse, error)
	CreateEnvironment(ctx context.Context, in *CreateEnvironmentRequest, opts ...grpc.CallOption) (*CreateEnvironmentResponse, error)
	ResetEnvironment(ctx context.Context, in *ResetEnvironmentRequest, opts ...grpc.CallOption) (*ResetEnvironmentResponse, error)
	StepEnvironment(ctx context.Context, in *StepEnvironmentRequest, opts ...grpc.CallOption) (*StepEnvironmentResponse, error)
	CloseEnvironment(ctx context.Context, in *CloseEnvironmentRequest, opts ...grpc.CallOption) (*CloseEnvironmentResponse, error)
	GetSpaces(ctx context.Context, in *GetSpacesRequest, opts ...grpc.CallOption) (*GetSpacesResponse, error)
}

type simulationServiceClient struct {
	cc grpc.ClientConnInterface
}

// NewSimulationServiceClient creates a new client
func NewSimulationServiceClient(cc grpc.ClientConnInterface) SimulationServiceClient {
	return &simulationServiceClient{cc}
}

func (c *simulationServiceClient) GetInfo(ctx context.Context, in *GetInfoRequest, opts ...grpc.CallOption) (*GetInfoResponse, error) {
	return nil, nil
}
func (c *simulationServiceClient) CreateEnvironment(ctx context.Context, in *CreateEnvironmentRequest, opts ...grpc.CallOption) (*CreateEnvironmentResponse, error) {
	return nil, nil
}
func (c *simulationServiceClient) ResetEnvironment(ctx context.Context, in *ResetEnvironmentRequest, opts ...grpc.CallOption) (*ResetEnvironmentResponse, error) {
	return nil, nil
}
func (c *simulationServiceClient) StepEnvironment(ctx context.Context, in *StepEnvironmentRequest, opts ...grpc.CallOption) (*StepEnvironmentResponse, error) {
	return nil, nil
}
func (c *simulationServiceClient) CloseEnvironment(ctx context.Context, in *CloseEnvironmentRequest, opts ...grpc.CallOption) (*CloseEnvironmentResponse, error) {
	return nil, nil
}
func (c *simulationServiceClient) GetSpaces(ctx context.Context, in *GetSpacesRequest, opts ...grpc.CallOption) (*GetSpacesResponse, error) {
	return nil, nil
}
