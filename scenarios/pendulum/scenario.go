package pendulum

import (
	"fmt"

	"github.com/jelech/rl_env_engine/core"
)

// PendulumScenario Pendulum场景实现
type PendulumScenario struct {
	name        string
	description string
}

// 确保PendulumScenario实现了core.Scenario接口
var _ core.Scenario = (*PendulumScenario)(nil)

// NewPendulumScenario 创建新的Pendulum场景
func NewPendulumScenario() *PendulumScenario {
	return &PendulumScenario{
		name:        "pendulum",
		description: "Classic Pendulum control environment - keep the pendulum upright",
	}
}

// GetName 获取场景名称
func (s *PendulumScenario) GetName() string {
	return s.name
}

// GetDescription 获取场景描述
func (s *PendulumScenario) GetDescription() string {
	return s.description
}

// CreateEnvironment 创建环境实例
func (s *PendulumScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
	env := NewPendulumEnvironment(config)
	return env, nil
}

// ValidateConfig 验证配置
func (s *PendulumScenario) ValidateConfig(config core.Config) error {
	// 验证max_steps
	if val := config.GetValue("max_steps"); val != nil {
		switch v := val.(type) {
		case int:
			if v <= 0 {
				return fmt.Errorf("max_steps must be positive, got %d", v)
			}
		case string:
			// 允许字符串形式的配置
		default:
			return fmt.Errorf("max_steps must be int or string, got %T", v)
		}
	}

	return nil
}

// GetSpaces 获取Pendulum场景的动作空间和观察空间定义
func (s *PendulumScenario) GetSpaces() core.SpaceDefinition {
	return core.SpaceDefinition{
		ActionSpace: core.ActionSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-2.0}, // 扭矩范围
			High:  []float64{2.0},
			Shape: []int32{1},
			Dtype: "float32",
		},
		ObservationSpace: core.ObservationSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-1.0, -1.0, -8.0}, // [cos(theta), sin(theta), theta_dot]
			High:  []float64{1.0, 1.0, 8.0},
			Shape: []int32{3},
			Dtype: "float32",
		},
	}
}
