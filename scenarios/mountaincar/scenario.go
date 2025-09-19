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
