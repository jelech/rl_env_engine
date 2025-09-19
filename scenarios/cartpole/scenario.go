package cartpole

import (
	"fmt"

	"github.com/jelech/rl_env_engine/core"
)

// CartPoleScenario CartPole场景实现
type CartPoleScenario struct {
	name        string
	description string
}

// 确保CartPoleScenario实现了core.Scenario接口
var _ core.Scenario = (*CartPoleScenario)(nil)

// NewCartPoleScenario 创建新的CartPole场景
func NewCartPoleScenario() *CartPoleScenario {
	return &CartPoleScenario{
		name:        "cartpole",
		description: "Classic CartPole control environment - balance a pole on a cart",
	}
}

// GetName 获取场景名称
func (s *CartPoleScenario) GetName() string {
	return s.name
}

// GetDescription 获取场景描述
func (s *CartPoleScenario) GetDescription() string {
	return s.description
}

// CreateEnvironment 创建环境实例
func (s *CartPoleScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
	env := NewCartPoleEnvironment(config)
	return env, nil
}

// ValidateConfig 验证配置
func (s *CartPoleScenario) ValidateConfig(config core.Config) error {
	// 验证max_steps
	if val := config.GetValue("max_steps"); val != nil {
		switch v := val.(type) {
		case int:
			if v <= 0 {
				return fmt.Errorf("max_steps must be positive, got %d", v)
			}
		case string:
			// 尝试解析字符串
			// 这里可以添加更严格的验证
		default:
			return fmt.Errorf("max_steps must be int or string, got %T", v)
		}
	}

	return nil
}

// GetSpaces 获取CartPole场景的动作空间和观察空间定义
func (s *CartPoleScenario) GetSpaces() core.SpaceDefinition {
	return core.SpaceDefinition{
		ActionSpace: core.ActionSpace{
			Type:  core.SpaceTypeDiscrete,
			Low:   []float64{0}, // 离散动作的最小值
			High:  []float64{1}, // 离散动作的最大值 (0: 左, 1: 右)
			Shape: []int32{},
			Dtype: "int32",
		},
		ObservationSpace: core.ObservationSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-4.8, -1e6, -0.42, -1e6}, // [x, x_dot, theta, theta_dot]
			High:  []float64{4.8, 1e6, 0.42, 1e6},
			Shape: []int32{4},
			Dtype: "float32",
		},
	}
}
