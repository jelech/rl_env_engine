package simple

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/jelech/rl_env_engine/core"
)

// SimpleEnvironment 简单的数学测试环境
// 目标：通过调整action让观察值接近目标值
type SimpleEnvironment struct {
	*core.BaseEnvironment
	currentValue float64
	targetValue  float64
	maxSteps     int
	currentStep  int
	tolerance    float64
	rng          *rand.Rand
}

// NewSimpleEnvironment 创建新的简单环境
func NewSimpleEnvironment(config core.Config) *SimpleEnvironment {
	baseEnv := core.NewBaseEnvironment("simple", "Simple mathematical test environment", config)

	// 从配置中获取参数，如果没有则使用默认值
	maxSteps := 100
	if val := config.GetValue("max_steps"); val != nil {
		switch v := val.(type) {
		case int:
			maxSteps = v
		case string:
			if parsed, err := strconv.Atoi(v); err == nil {
				maxSteps = parsed
			}
		}
	}

	tolerance := 0.1
	if val := config.GetValue("tolerance"); val != nil {
		switch v := val.(type) {
		case float64:
			tolerance = v
		case float32:
			tolerance = float64(v)
		case string:
			if parsed, err := strconv.ParseFloat(v, 64); err == nil {
				tolerance = parsed
			}
		}
	}

	return &SimpleEnvironment{
		BaseEnvironment: baseEnv,
		currentValue:    0.0,
		targetValue:     10.0, // 目标值
		maxSteps:        maxSteps,
		currentStep:     0,
		tolerance:       tolerance,
		rng:             rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// Reset 重置环境到初始状态
func (e *SimpleEnvironment) Reset(ctx context.Context) ([]core.Observation, error) {
	// 重置状态
	e.currentValue = 0.0
	e.targetValue = e.rng.Float64()*20.0 - 10.0 // 随机目标值 [-10, 10]
	e.currentStep = 0

	// 返回初始观察
	return e.GetObservations(), nil
}

// Step 执行一步仿真
func (e *SimpleEnvironment) Step(ctx context.Context, actions []core.Action) ([]core.Observation, []float64, []bool, error) {
	if len(actions) == 0 {
		return nil, nil, nil, fmt.Errorf("no actions provided")
	}

	// 从GenericAction中提取数值
	var actionValue float64

	// 首先尝试使用GenericAction
	if genericAction, ok := actions[0].(*core.GenericAction); ok {
		var err error
		actionValue, err = genericAction.GetFloat64()
		if err != nil {
			return nil, nil, nil, fmt.Errorf("failed to extract float64 from generic action: %w", err)
		}
	} else if simpleAction, ok := actions[0].(*SimpleAction); ok {
		// 兼容旧的SimpleAction
		actionValue = simpleAction.Value
	} else {
		return nil, nil, nil, fmt.Errorf("invalid action type: %T", actions[0])
	}

	// 应用action：简单地将action值添加到当前值
	e.currentValue += actionValue
	e.currentStep++

	// 计算奖励：距离目标值越近奖励越高
	distance := math.Abs(e.currentValue - e.targetValue)
	reward := -distance // 负距离作为奖励，距离越小奖励越高

	// 如果非常接近目标，给予额外奖励
	if distance < e.tolerance {
		reward += 10.0
	}

	// 检查是否完成
	done := e.currentStep >= e.maxSteps || distance < e.tolerance

	observations := e.GetObservations()
	rewards := []float64{reward}
	doneFlags := []bool{done}

	return observations, rewards, doneFlags, nil
}

// GetObservations 获取当前观察
func (e *SimpleEnvironment) GetObservations() []core.Observation {
	obs := NewSimpleObservation(e.currentValue, e.targetValue, float64(e.currentStep), float64(e.maxSteps))
	return []core.Observation{obs}
}

// GetReward 计算当前奖励
func (e *SimpleEnvironment) GetReward() []float64 {
	distance := math.Abs(e.currentValue - e.targetValue)
	reward := -distance
	if distance < e.tolerance {
		reward += 10.0
	}
	return []float64{reward}
}

// SimpleObservation 简单观察实现
type SimpleObservation struct {
	*core.BaseObservation
}

// NewSimpleObservation 创建新的简单观察
func NewSimpleObservation(currentValue, targetValue, currentStep, maxSteps float64) *SimpleObservation {
	data := []float64{
		currentValue,
		targetValue,
		targetValue - currentValue, // 距离目标的差值
		currentStep,
		maxSteps,
		currentStep / maxSteps, // 进度比例
	}

	metadata := map[string]interface{}{
		"current_value": currentValue,
		"target_value":  targetValue,
		"current_step":  currentStep,
		"max_steps":     maxSteps,
		"distance":      math.Abs(currentValue - targetValue),
	}

	baseObs := core.NewBaseObservation(data, metadata)
	return &SimpleObservation{
		BaseObservation: baseObs,
	}
}

// SimpleAction 简单行动实现
type SimpleAction struct {
	Value float64 // 要添加到当前值的数值
}

// NewSimpleAction 创建新的简单行动
func NewSimpleAction(value float64) *SimpleAction {
	return &SimpleAction{
		Value: value,
	}
}

// GetData 获取行动数据
func (a *SimpleAction) GetData() interface{} {
	return a.Value
}

// Validate 验证行动
func (a *SimpleAction) Validate() error {
	return nil
}
