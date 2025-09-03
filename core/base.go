package core

import (
	"context"
	"fmt"
)

// BaseObservation 基础观察实现
type BaseObservation struct {
	data     []float64
	metadata map[string]interface{}
}

func NewBaseObservation(data []float64, metadata map[string]interface{}) *BaseObservation {
	if metadata == nil {
		metadata = make(map[string]interface{})
	}
	return &BaseObservation{
		data:     data,
		metadata: metadata,
	}
}

func (o *BaseObservation) GetData() []float64 {
	return o.data
}

func (o *BaseObservation) GetMetadata() map[string]interface{} {
	return o.metadata
}

// BaseConfig 基础配置实现
type BaseConfig struct {
	values map[string]interface{}
}

func NewBaseConfig() *BaseConfig {
	return &BaseConfig{
		values: make(map[string]interface{}),
	}
}

func (c *BaseConfig) GetValue(key string) interface{} {
	return c.values[key]
}

func (c *BaseConfig) SetValue(key string, value interface{}) {
	c.values[key] = value
}

func (c *BaseConfig) Validate() error {
	// 基础配置验证，子类可以重写
	return nil
}

// BaseEnvironment 基础环境实现
type BaseEnvironment struct {
	name        string
	description string
	config      Config
	dataLoader  DataLoader
	strategy    Strategy
	state       interface{}
	metadata    map[string]interface{}
}

func NewBaseEnvironment(name, description string, config Config) *BaseEnvironment {
	return &BaseEnvironment{
		name:        name,
		description: description,
		config:      config,
		metadata:    make(map[string]interface{}),
	}
}

func (e *BaseEnvironment) SetDataLoader(loader DataLoader) {
	e.dataLoader = loader
}

func (e *BaseEnvironment) SetStrategy(strategy Strategy) {
	e.strategy = strategy
}

func (e *BaseEnvironment) GetInfo() map[string]interface{} {
	info := make(map[string]interface{})
	info["name"] = e.name
	info["description"] = e.description
	for k, v := range e.metadata {
		info[k] = v
	}
	return info
}

func (e *BaseEnvironment) Reset(ctx context.Context) ([]Observation, error) {
	// 基础重置逻辑，子类需要实现具体逻辑
	return nil, fmt.Errorf("reset method must be implemented by subclass")
}

func (e *BaseEnvironment) Step(ctx context.Context, actions []Action) ([]Observation, []float64, []bool, error) {
	// 基础步进逻辑，子类需要实现具体逻辑
	return nil, nil, nil, fmt.Errorf("step method must be implemented by subclass")
}

func (e *BaseEnvironment) GetObservations() []Observation {
	// 子类需要实现
	return nil
}

func (e *BaseEnvironment) GetReward() []float64 {
	// 子类需要实现
	return nil
}

func (e *BaseEnvironment) Close() error {
	// 基础清理逻辑
	e.state = nil
	return nil
}

// SimulationEngine 仿真引擎
type SimulationEngine struct {
	scenarios map[string]Scenario
}

func NewSimulationEngine() *SimulationEngine {
	return &SimulationEngine{
		scenarios: make(map[string]Scenario),
	}
}

func (s *SimulationEngine) RegisterScenario(scenario Scenario) {
	s.scenarios[scenario.GetName()] = scenario
}

func (s *SimulationEngine) GetScenario(name string) (Scenario, error) {
	scenario, exists := s.scenarios[name]
	if !exists {
		return nil, fmt.Errorf("scenario '%s' not found", name)
	}
	return scenario, nil
}

func (s *SimulationEngine) ListScenarios() []string {
	var names []string
	for name := range s.scenarios {
		names = append(names, name)
	}
	return names
}

func (s *SimulationEngine) CreateEnvironment(scenarioName string, config Config) (Environment, error) {
	scenario, err := s.GetScenario(scenarioName)
	if err != nil {
		return nil, err
	}

	if err := scenario.ValidateConfig(config); err != nil {
		return nil, fmt.Errorf("invalid config for scenario '%s': %w", scenarioName, err)
	}

	return scenario.CreateEnvironment(config)
}
