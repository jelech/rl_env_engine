package mountaincar

import (
	"fmt"

	"github.com/jelech/rl_env_engine/core"
)

// MountainCarScenario MountainCar场景实现
type MountainCarScenario struct {
	name        string
	description string
}

// 确保MountainCarScenario实现了core.Scenario接口
var _ core.Scenario = (*MountainCarScenario)(nil)

// NewMountainCarScenario 创建新的MountainCar场景
func NewMountainCarScenario() *MountainCarScenario {
	return &MountainCarScenario{
		name:        "mountaincar",
		description: "Classic MountainCar control environment - get the car to the top of the right hill",
	}
}

// GetName 获取场景名称
func (s *MountainCarScenario) GetName() string {
	return s.name
}

// GetDescription 获取场景描述
func (s *MountainCarScenario) GetDescription() string {
	return s.description
}

// CreateEnvironment 创建环境实例
func (s *MountainCarScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
	env := NewMountainCarEnvironment(config)
	return env, nil
}

// ValidateConfig 验证配置
func (s *MountainCarScenario) ValidateConfig(config core.Config) error {
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

// GetSpaces 获取MountainCar场景的动作空间和观察空间定义
func (s *MountainCarScenario) GetSpaces() core.SpaceDefinition {
	return core.SpaceDefinition{
		ActionSpace: core.ActionSpace{
			Type:  core.SpaceTypeDiscrete,
			Low:   []float64{0}, // 离散动作的最小值
			High:  []float64{2}, // 离散动作的最大值 (0: 左, 1: 不动, 2: 右)
			Shape: []int32{},
			Dtype: "int32",
		},
		ObservationSpace: core.ObservationSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-1.2, -0.07}, // [position, velocity]
			High:  []float64{0.6, 0.07},
			Shape: []int32{2},
			Dtype: "float32",
		},
	}
}
