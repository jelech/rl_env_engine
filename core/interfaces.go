package core

import "context"

// Observation 表示环境的观察状态
type Observation interface {
	GetData() []float64
	GetMetadata() map[string]interface{}
}

// Action 表示智能体的行动
type Action interface {
	GetData() interface{}
	Validate() error
}

// Environment 定义仿真环境的通用接口
type Environment interface {
	// Reset 重置环境到初始状态
	Reset(ctx context.Context) ([]Observation, error)

	// Step 执行一步仿真
	Step(ctx context.Context, actions []Action) ([]Observation, []float64, []bool, error)

	// GetObservations 获取当前观察状态
	GetObservations() []Observation

	// GetReward 计算奖励
	GetReward() []float64

	// GetInfo 获取环境信息
	GetInfo() map[string]interface{}

	// GetSpaces 获取环境的动作空间和观察空间定义
	GetSpaces() SpaceDefinition

	// Close 关闭环境
	Close() error
}

// Scenario 定义场景接口，不同的场景可以有不同的实现
type Scenario interface {
	// GetName 获取场景名称
	GetName() string

	// GetDescription 获取场景描述
	GetDescription() string

	// CreateEnvironment 创建该场景对应的环境
	CreateEnvironment(config Config) (Environment, error)

	// ValidateConfig 验证配置
	ValidateConfig(config Config) error
}

// Config 定义配置接口
type Config interface {
	GetValue(key string) interface{}
	SetValue(key string, value interface{})
	Validate() error
}

// DataLoader 定义数据加载器接口
type DataLoader interface {
	Load(path string) (interface{}, error)
	Validate(data interface{}) error
}

// Strategy 定义策略接口
type Strategy interface {
	GetName() string
	Execute(state interface{}, actions []Action) (interface{}, error)
}
