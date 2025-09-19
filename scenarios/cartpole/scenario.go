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
