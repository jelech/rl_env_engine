package simple

import (
	"fmt"
	"strconv"

	"github.com/jelech/rl_env_engine/core"
)

// SimpleScenario 简单场景实现
type SimpleScenario struct {
	name        string
	description string
}

var _ core.Scenario = (*SimpleScenario)(nil)

// NewSimpleScenario 创建新的简单场景
func NewSimpleScenario() *SimpleScenario {
	return &SimpleScenario{
		name:        "simple",
		description: "Simple mathematical test scenario for debugging and development",
	}
}

// GetName 获取场景名称
func (s *SimpleScenario) GetName() string {
	return s.name
}

// GetDescription 获取场景描述
func (s *SimpleScenario) GetDescription() string {
	return s.description
}

// CreateEnvironment 创建环境
func (s *SimpleScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
	if err := s.ValidateConfig(config); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}

	env := NewSimpleEnvironment(config)
	return env, nil
}

// ValidateConfig 验证配置
func (s *SimpleScenario) ValidateConfig(config core.Config) error {
	if config == nil {
		return fmt.Errorf("config cannot be nil")
	}

	// 验证max_steps参数
	if val := config.GetValue("max_steps"); val != nil {
		var steps int
		switch v := val.(type) {
		case int:
			steps = v
		case string:
			if parsed, err := strconv.Atoi(v); err != nil {
				return fmt.Errorf("max_steps must be a valid integer, got %s", v)
			} else {
				steps = parsed
			}
		default:
			return fmt.Errorf("max_steps must be an integer or string, got %T", val)
		}

		if steps <= 0 || steps > 1000 {
			return fmt.Errorf("max_steps must be between 1 and 1000, got %d", steps)
		}
	}

	// 验证tolerance参数
	if val := config.GetValue("tolerance"); val != nil {
		var tol float64
		switch v := val.(type) {
		case float64:
			tol = v
		case float32:
			tol = float64(v)
		case string:
			if parsed, err := strconv.ParseFloat(v, 64); err != nil {
				return fmt.Errorf("tolerance must be a valid float, got %s", v)
			} else {
				tol = parsed
			}
		default:
			return fmt.Errorf("tolerance must be a float or string, got %T", val)
		}

		if tol <= 0 || tol > 10 {
			return fmt.Errorf("tolerance must be between 0 and 10, got %f", tol)
		}
	}

	return nil
}

// GetSpaces 获取简单场景的动作空间和观察空间定义
func (s *SimpleScenario) GetSpaces() core.SpaceDefinition {
	return core.SpaceDefinition{
		ActionSpace: core.ActionSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-10.0},
			High:  []float64{10.0},
			Shape: []int32{1},
			Dtype: "float32",
		},
		ObservationSpace: core.ObservationSpace{
			Type:  core.SpaceTypeBox,
			Low:   []float64{-1000000, -1000000, 0, 0, 0, -1000000}, // [current, target, step, max_steps, tolerance, reward]
			High:  []float64{1000000, 1000000, 1000000, 1000000, 1000000, 1000000},
			Shape: []int32{6},
			Dtype: "float32",
		},
	}
}
