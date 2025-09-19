package cartpole

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/jelech/rl_env_engine/core"
)

// CartPoleEnvironment 经典的平衡杆控制环境
// 目标：通过向左或向右移动小车来保持杆子平衡
type CartPoleEnvironment struct {
	*core.BaseEnvironment
	// 状态变量
	x        float64 // 小车位置
	xDot     float64 // 小车速度
	theta    float64 // 杆子角度 (radians)
	thetaDot float64 // 杆子角速度

	// 环境参数
	maxSteps       int
	currentStep    int
	gravity        float64
	masscart       float64
	masspole       float64
	totalMass      float64
	length         float64 // 实际上是杆子长度的一半
	polemassLength float64
	forceMag       float64
	tau            float64 // 时间步长

	// 阈值
	thetaThresholdRadians float64
	xThreshold            float64

	rng *rand.Rand
}

// NewCartPoleEnvironment 创建新的CartPole环境
func NewCartPoleEnvironment(config core.Config) *CartPoleEnvironment {
	baseEnv := core.NewBaseEnvironment("cartpole", "Classic CartPole control environment", config)

	// 从配置中获取参数，如果没有则使用默认值
	maxSteps := 500
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

	// 物理参数（基于OpenAI Gym的CartPole-v1）
	gravity := 9.8
	masscart := 1.0
	masspole := 0.1
	totalMass := masspole + masscart
	length := 0.5 // 实际上是杆子长度的一半
	polemassLength := masspole * length
	forceMag := 10.0
	tau := 0.02 // 50 FPS

	// 阈值
	thetaThresholdRadians := 12 * 2 * math.Pi / 360 // ±12°
	xThreshold := 2.4

	env := &CartPoleEnvironment{
		BaseEnvironment:       baseEnv,
		maxSteps:              maxSteps,
		currentStep:           0,
		gravity:               gravity,
		masscart:              masscart,
		masspole:              masspole,
		totalMass:             totalMass,
		length:                length,
		polemassLength:        polemassLength,
		forceMag:              forceMag,
		tau:                   tau,
		thetaThresholdRadians: thetaThresholdRadians,
		xThreshold:            xThreshold,
		rng:                   rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	return env
}

// Reset 重置环境
func (e *CartPoleEnvironment) Reset(ctx context.Context) ([]core.Observation, error) {
	// 随机初始化状态（小范围）
	e.x = e.rng.Float64()*0.1 - 0.05        // [-0.05, 0.05]
	e.xDot = e.rng.Float64()*0.1 - 0.05     // [-0.05, 0.05]
	e.theta = e.rng.Float64()*0.1 - 0.05    // [-0.05, 0.05] radians
	e.thetaDot = e.rng.Float64()*0.1 - 0.05 // [-0.05, 0.05] rad/s

	e.currentStep = 0

	return e.GetObservations(), nil
}

// Step 执行一步
func (e *CartPoleEnvironment) Step(ctx context.Context, actions []core.Action) ([]core.Observation, []float64, []bool, error) {
	if len(actions) == 0 {
		return nil, nil, nil, fmt.Errorf("no actions provided")
	}

	e.currentStep++

	// 解析动作（0: 向左推, 1: 向右推）
	var force float64

	// 尝试从GenericAction中提取
	if genericAction, ok := actions[0].(*core.GenericAction); ok {
		actionValue, err := genericAction.GetFloat64()
		if err != nil {
			return nil, nil, nil, fmt.Errorf("failed to extract action value: %w", err)
		}
		// 将连续动作转换为离散动作
		if actionValue < 0.5 {
			force = -e.forceMag
		} else {
			force = e.forceMag
		}
	} else if cartPoleAction, ok := actions[0].(*CartPoleAction); ok {
		// 使用CartPole专用动作
		if cartPoleAction.Action == 0 {
			force = -e.forceMag
		} else {
			force = e.forceMag
		}
	} else {
		return nil, nil, nil, fmt.Errorf("unsupported action type: %T", actions[0])
	}

	// 物理仿真（使用Euler方法）
	costheta := math.Cos(e.theta)
	sintheta := math.Sin(e.theta)

	temp := (force + e.polemassLength*e.thetaDot*e.thetaDot*sintheta) / e.totalMass
	thetaacc := (e.gravity*sintheta - costheta*temp) / (e.length * (4.0/3.0 - e.masspole*costheta*costheta/e.totalMass))
	xacc := temp - e.polemassLength*thetaacc*costheta/e.totalMass

	// 更新状态
	e.x += e.tau * e.xDot
	e.xDot += e.tau * xacc
	e.theta += e.tau * e.thetaDot
	e.thetaDot += e.tau * thetaacc

	// 检查是否结束
	done := e.x < -e.xThreshold || e.x > e.xThreshold ||
		e.theta < -e.thetaThresholdRadians || e.theta > e.thetaThresholdRadians ||
		e.currentStep >= e.maxSteps

	// 奖励：每一步都给1分，直到失败
	reward := 1.0
	if done && e.currentStep < e.maxSteps {
		reward = 0.0 // 失败时不给奖励
	}

	observations := e.GetObservations()
	rewards := []float64{reward}
	dones := []bool{done}

	return observations, rewards, dones, nil
}

// GetObservations 获取当前观察
func (e *CartPoleEnvironment) GetObservations() []core.Observation {
	data := []float64{
		e.x,        // 小车位置
		e.xDot,     // 小车速度
		e.theta,    // 杆子角度
		e.thetaDot, // 杆子角速度
	}

	metadata := map[string]interface{}{
		"x":         e.x,
		"x_dot":     e.xDot,
		"theta":     e.theta,
		"theta_dot": e.thetaDot,
		"step":      e.currentStep,
		"max_steps": e.maxSteps,
	}

	observation := core.NewBaseObservation(data, metadata)
	return []core.Observation{observation}
}

// GetReward 计算奖励
func (e *CartPoleEnvironment) GetReward() []float64 {
	// 检查是否结束
	done := e.x < -e.xThreshold || e.x > e.xThreshold ||
		e.theta < -e.thetaThresholdRadians || e.theta > e.thetaThresholdRadians ||
		e.currentStep >= e.maxSteps

	// 奖励：每一步都给1分，直到失败
	reward := 1.0
	if done && e.currentStep < e.maxSteps {
		reward = 0.0 // 失败时不给奖励
	}

	return []float64{reward}
}

// Close 关闭环境
func (e *CartPoleEnvironment) Close() error {
	return e.BaseEnvironment.Close()
}

// CartPoleAction CartPole专用动作
type CartPoleAction struct {
	Action int // 0: 左, 1: 右
}

// NewCartPoleAction 创建新的CartPole动作
func NewCartPoleAction(action int) *CartPoleAction {
	return &CartPoleAction{Action: action}
}

// GetData 获取动作数据
func (a *CartPoleAction) GetData() interface{} {
	return a.Action
}

// Validate 验证动作
func (a *CartPoleAction) Validate() error {
	if a.Action != 0 && a.Action != 1 {
		return fmt.Errorf("cartpole action must be 0 (left) or 1 (right), got %d", a.Action)
	}
	return nil
}
