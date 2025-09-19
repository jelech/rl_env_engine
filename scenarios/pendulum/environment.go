package pendulum

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/jelech/rl_env_engine/core"
)

// PendulumEnvironment 经典的倒立摆控制环境
// 目标：通过施加扭矩来保持摆锤直立
type PendulumEnvironment struct {
	*core.BaseEnvironment
	// 状态变量
	theta    float64 // 角度 (radians)
	thetaDot float64 // 角速度 (rad/s)

	// 环境参数
	maxSteps    int
	currentStep int
	maxSpeed    float64
	maxTorque   float64
	dt          float64 // 时间步长
	g           float64 // 重力加速度
	m           float64 // 摆锤质量
	l           float64 // 摆锤长度

	rng *rand.Rand
}

// NewPendulumEnvironment 创建新的Pendulum环境
func NewPendulumEnvironment(config core.Config) *PendulumEnvironment {
	baseEnv := core.NewBaseEnvironment("pendulum", "Classic Pendulum control environment", config)

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

	// 环境参数（基于OpenAI Gym的Pendulum-v1）
	maxSpeed := 8.0
	maxTorque := 2.0
	dt := 0.05
	g := 10.0
	m := 1.0
	l := 1.0

	env := &PendulumEnvironment{
		BaseEnvironment: baseEnv,
		maxSteps:        maxSteps,
		currentStep:     0,
		maxSpeed:        maxSpeed,
		maxTorque:       maxTorque,
		dt:              dt,
		g:               g,
		m:               m,
		l:               l,
		rng:             rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	return env
}

// Reset 重置环境
func (e *PendulumEnvironment) Reset(ctx context.Context) ([]core.Observation, error) {
	// 随机初始化角度和角速度
	e.theta = e.rng.Float64()*2*math.Pi - math.Pi // [-π, π]
	e.thetaDot = e.rng.Float64()*2 - 1            // [-1, 1]
	e.currentStep = 0

	return e.GetObservations(), nil
}

// Step 执行一步
func (e *PendulumEnvironment) Step(ctx context.Context, actions []core.Action) ([]core.Observation, []float64, []bool, error) {
	if len(actions) == 0 {
		return nil, nil, nil, fmt.Errorf("no actions provided")
	}

	e.currentStep++

	// 解析动作（连续扭矩值）
	var torque float64

	// 尝试从GenericAction中提取
	if genericAction, ok := actions[0].(*core.GenericAction); ok {
		var err error
		torque, err = genericAction.GetFloat64()
		if err != nil {
			return nil, nil, nil, fmt.Errorf("failed to extract action value: %w", err)
		}
	} else if pendulumAction, ok := actions[0].(*PendulumAction); ok {
		torque = pendulumAction.Torque
	} else {
		return nil, nil, nil, fmt.Errorf("unsupported action type: %T", actions[0])
	}

	// 限制扭矩
	if torque > e.maxTorque {
		torque = e.maxTorque
	} else if torque < -e.maxTorque {
		torque = -e.maxTorque
	}

	// 计算成本（cost，负奖励）
	costs := angleNormalize(e.theta)*angleNormalize(e.theta) + 0.1*e.thetaDot*e.thetaDot + 0.001*torque*torque

	// 物理仿真
	newThetaDot := e.thetaDot + (3*e.g/(2*e.l)*math.Sin(e.theta)+3.0/(e.m*e.l*e.l)*torque)*e.dt
	if newThetaDot > e.maxSpeed {
		newThetaDot = e.maxSpeed
	} else if newThetaDot < -e.maxSpeed {
		newThetaDot = -e.maxSpeed
	}

	e.theta += newThetaDot * e.dt
	e.thetaDot = newThetaDot

	// 检查是否结束（Pendulum通常不会提前结束）
	done := e.currentStep >= e.maxSteps

	// 奖励是负成本
	reward := -costs

	observations := e.GetObservations()
	rewards := []float64{reward}
	dones := []bool{done}

	return observations, rewards, dones, nil
}

// GetObservations 获取当前观察
func (e *PendulumEnvironment) GetObservations() []core.Observation {
	// Pendulum的观察是 [cos(theta), sin(theta), theta_dot]
	data := []float64{
		math.Cos(e.theta),
		math.Sin(e.theta),
		e.thetaDot,
	}

	metadata := map[string]interface{}{
		"theta":     e.theta,
		"theta_dot": e.thetaDot,
		"step":      e.currentStep,
		"max_steps": e.maxSteps,
	}

	observation := core.NewBaseObservation(data, metadata)
	return []core.Observation{observation}
}

// GetReward 计算奖励
func (e *PendulumEnvironment) GetReward() []float64 {
	// 这里假设没有扭矩的基础成本
	costs := angleNormalize(e.theta)*angleNormalize(e.theta) + 0.1*e.thetaDot*e.thetaDot
	reward := -costs
	return []float64{reward}
}

// Close 关闭环境
func (e *PendulumEnvironment) Close() error {
	return e.BaseEnvironment.Close()
}

// GetSpaces 获取Pendulum场景的动作空间和观察空间定义
func (e *PendulumEnvironment) GetSpaces() core.SpaceDefinition {
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

// angleNormalize 将角度规范化到 [-π, π]
func angleNormalize(x float64) float64 {
	return math.Mod(x+math.Pi, 2*math.Pi) - math.Pi
}

// PendulumAction Pendulum专用动作
type PendulumAction struct {
	Torque float64 // 施加的扭矩
}

// NewPendulumAction 创建新的Pendulum动作
func NewPendulumAction(torque float64) *PendulumAction {
	return &PendulumAction{Torque: torque}
}

// GetData 获取动作数据
func (a *PendulumAction) GetData() interface{} {
	return a.Torque
}

// Validate 验证动作
func (a *PendulumAction) Validate() error {
	if math.Abs(a.Torque) > 2.0 {
		return fmt.Errorf("pendulum torque must be in range [-2.0, 2.0], got %f", a.Torque)
	}
	return nil
}
