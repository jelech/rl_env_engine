package mountaincar

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/jelech/rl_env_engine/core"
)

// MountainCarEnvironment 经典的小车上山环境
// 目标：通过向左或向右加速来让小车到达右侧山顶
type MountainCarEnvironment struct {
	*core.BaseEnvironment
	// 状态变量
	position float64 // 小车位置
	velocity float64 // 小车速度

	// 环境参数
	maxSteps     int
	currentStep  int
	minPosition  float64
	maxPosition  float64
	maxSpeed     float64
	goalPosition float64
	goalVelocity float64
	force        float64
	gravity      float64

	rng *rand.Rand
}

// NewMountainCarEnvironment 创建新的MountainCar环境
func NewMountainCarEnvironment(config core.Config) *MountainCarEnvironment {
	baseEnv := core.NewBaseEnvironment("mountaincar", "Classic MountainCar control environment", config)

	// 从配置中获取参数
	maxSteps := 200
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

	// 环境参数（基于OpenAI Gym的MountainCar-v0）
	minPosition := -1.2
	maxPosition := 0.6
	maxSpeed := 0.07
	goalPosition := 0.5
	goalVelocity := 0.0
	force := 0.001
	gravity := 0.0025

	env := &MountainCarEnvironment{
		BaseEnvironment: baseEnv,
		maxSteps:        maxSteps,
		currentStep:     0,
		minPosition:     minPosition,
		maxPosition:     maxPosition,
		maxSpeed:        maxSpeed,
		goalPosition:    goalPosition,
		goalVelocity:    goalVelocity,
		force:           force,
		gravity:         gravity,
		rng:             rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	return env
}

// Reset 重置环境
func (e *MountainCarEnvironment) Reset(ctx context.Context) ([]core.Observation, error) {
	// 随机初始化位置，速度为0
	e.position = e.rng.Float64()*0.6 - 1.2 // [-1.2, -0.6]
	e.velocity = 0.0
	e.currentStep = 0

	return e.GetObservations(), nil
}

// Step 执行一步
func (e *MountainCarEnvironment) Step(ctx context.Context, actions []core.Action) ([]core.Observation, []float64, []bool, error) {
	if len(actions) == 0 {
		return nil, nil, nil, fmt.Errorf("no actions provided")
	}

	e.currentStep++

	// 解析动作（0: 向左加速, 1: 不加速, 2: 向右加速）
	var actionValue int

	// 尝试从GenericAction中提取
	if genericAction, ok := actions[0].(*core.GenericAction); ok {
		actionFloat, err := genericAction.GetFloat64()
		if err != nil {
			return nil, nil, nil, fmt.Errorf("failed to extract action value: %w", err)
		}
		// 将连续动作转换为离散动作
		if actionFloat < 0.33 {
			actionValue = 0 // 向左
		} else if actionFloat < 0.67 {
			actionValue = 1 // 不动
		} else {
			actionValue = 2 // 向右
		}
	} else if mountainCarAction, ok := actions[0].(*MountainCarAction); ok {
		actionValue = mountainCarAction.Action
	} else {
		return nil, nil, nil, fmt.Errorf("unsupported action type: %T", actions[0])
	}

	// 计算新速度
	e.velocity += (float64(actionValue)-1.0)*e.force + math.Cos(3.0*e.position)*(-e.gravity)

	// 限制速度
	if e.velocity < -e.maxSpeed {
		e.velocity = -e.maxSpeed
	} else if e.velocity > e.maxSpeed {
		e.velocity = e.maxSpeed
	}

	// 更新位置
	e.position += e.velocity

	// 限制位置
	if e.position < e.minPosition {
		e.position = e.minPosition
		e.velocity = 0.0 // 撞到左边界，速度归零
	} else if e.position > e.maxPosition {
		e.position = e.maxPosition
	}

	// 检查是否到达目标
	done := e.position >= e.goalPosition || e.currentStep >= e.maxSteps

	// 奖励：到达目标给0，否则给-1（鼓励尽快到达）
	reward := -1.0
	if e.position >= e.goalPosition {
		reward = 0.0
	}

	observations := e.GetObservations()
	rewards := []float64{reward}
	dones := []bool{done}

	return observations, rewards, dones, nil
}

// GetObservations 获取当前观察
func (e *MountainCarEnvironment) GetObservations() []core.Observation {
	data := []float64{
		e.position, // 小车位置
		e.velocity, // 小车速度
	}

	metadata := map[string]interface{}{
		"position":     e.position,
		"velocity":     e.velocity,
		"step":         e.currentStep,
		"max_steps":    e.maxSteps,
		"goal_reached": e.position >= e.goalPosition,
	}

	observation := core.NewBaseObservation(data, metadata)
	return []core.Observation{observation}
}

// GetReward 计算奖励
func (e *MountainCarEnvironment) GetReward() []float64 {
	// 到达目标给0，否则给-1
	reward := -1.0
	if e.position >= e.goalPosition {
		reward = 0.0
	}
	return []float64{reward}
}

// Close 关闭环境
func (e *MountainCarEnvironment) Close() error {
	return e.BaseEnvironment.Close()
}

// GetSpaces 获取MountainCar场景的动作空间和观察空间定义
func (e *MountainCarEnvironment) GetSpaces() core.SpaceDefinition {
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

// MountainCarAction MountainCar专用动作
type MountainCarAction struct {
	Action int // 0: 向左, 1: 不动, 2: 向右
}

// NewMountainCarAction 创建新的MountainCar动作
func NewMountainCarAction(action int) *MountainCarAction {
	return &MountainCarAction{Action: action}
}

// GetData 获取动作数据
func (a *MountainCarAction) GetData() interface{} {
	return a.Action
}

// Validate 验证动作
func (a *MountainCarAction) Validate() error {
	if a.Action < 0 || a.Action > 2 {
		return fmt.Errorf("mountaincar action must be 0 (left), 1 (none), or 2 (right), got %d", a.Action)
	}
	return nil
}
