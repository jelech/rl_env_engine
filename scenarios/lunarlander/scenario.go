package lunarlander

import (
	"fmt"

	"github.com/jelech/rl_env_engine/core"
)

// LunarLanderScenario LunarLander场景实现
type LunarLanderScenario struct {
	name        string
	description string
}

// 确保LunarLanderScenario实现了core.Scenario接口
var _ core.Scenario = (*LunarLanderScenario)(nil)

// NewLunarLanderScenario 创建新的LunarLander场景
func NewLunarLanderScenario() *LunarLanderScenario {
	return &LunarLanderScenario{
		name:        "lunarlander",
		description: "Classic LunarLander control environment - land the spacecraft on the landing pad",
	}
}

// GetName 获取场景名称
func (s *LunarLanderScenario) GetName() string {
	return s.name
}

// GetDescription 获取场景描述
func (s *LunarLanderScenario) GetDescription() string {
	return s.description
}

// CreateEnvironment 创建环境实例
func (s *LunarLanderScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
	env := NewLunarLanderEnvironment(config)
	return env, nil
}

// ValidateConfig 验证配置
func (s *LunarLanderScenario) ValidateConfig(config core.Config) error {
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

// GetSpaces 获取LunarLander场景的动作空间和观察空间定义
func (s *LunarLanderScenario) GetSpaces() core.SpaceDefinition {
	return core.SpaceDefinition{
		ActionSpace: core.ActionSpace{
			Type:  core.SpaceTypeDiscrete,
			Low:   []float64{0}, // 离散动作的最小值
			High:  []float64{3}, // 离散动作的最大值 (0: noop, 1: left, 2: main, 3: right)
			Shape: []int32{},
			Dtype: "int32",
		},
		ObservationSpace: core.ObservationSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-1.5, -5.0, -5.0, -5.0, -3.14159, -5.0, 0.0, 0.0}, // [x, y, vel_x, vel_y, angle, angular_vel, left_leg, right_leg]
			High:  []float64{1.5, 5.0, 5.0, 5.0, 3.14159, 5.0, 1.0, 1.0},
			Shape: []int32{8},
			Dtype: "float32",
		},
	}
}
