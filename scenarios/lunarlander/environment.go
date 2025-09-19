package lunarlander

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"strconv"
	"time"

	"github.com/jelech/rl_env_engine/core"
)

// LunarLanderEnvironment 简化版的月球着陆器控制环境
// 目标：安全着陆在指定区域
type LunarLanderEnvironment struct {
	*core.BaseEnvironment
	// 状态变量
	x        float64 // 水平位置
	y        float64 // 垂直位置
	vx       float64 // 水平速度
	vy       float64 // 垂直速度
	angle    float64 // 着陆器角度
	angularV float64 // 角速度

	// 环境参数
	maxSteps     int
	currentStep  int
	gravity      float64
	thrustPower  float64
	lateralPower float64
	dt           float64
	landingPadX  float64
	landingPadY  float64
	landingPadW  float64
	crashed      bool
	landed       bool

	rng *rand.Rand
}

// NewLunarLanderEnvironment 创建新的LunarLander环境
func NewLunarLanderEnvironment(config core.Config) *LunarLanderEnvironment {
	baseEnv := core.NewBaseEnvironment("lunarlander", "Simplified Lunar Lander control environment", config)

	// 从配置中获取参数
	maxSteps := 400
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

	// 环境参数
	gravity := 1.6      // 月球重力
	thrustPower := 13.0 // 主推进器功率
	lateralPower := 0.6 // 侧推进器功率
	dt := 1.0 / 60.0    // 60 FPS
	landingPadX := 0.0  // 着陆区中心X
	landingPadY := 0.0  // 着陆区Y
	landingPadW := 0.3  // 着陆区宽度

	env := &LunarLanderEnvironment{
		BaseEnvironment: baseEnv,
		maxSteps:        maxSteps,
		currentStep:     0,
		gravity:         gravity,
		thrustPower:     thrustPower,
		lateralPower:    lateralPower,
		dt:              dt,
		landingPadX:     landingPadX,
		landingPadY:     landingPadY,
		landingPadW:     landingPadW,
		crashed:         false,
		landed:          false,
		rng:             rand.New(rand.NewSource(time.Now().UnixNano())),
	}

	return env
}

// Reset 重置环境
func (e *LunarLanderEnvironment) Reset(ctx context.Context) ([]core.Observation, error) {
	// 随机初始化位置和速度
	e.x = e.rng.Float64()*2 - 1      // [-1, 1]
	e.y = e.rng.Float64()*0.5 + 1.5  // [1.5, 2.0] 从高处开始
	e.vx = e.rng.Float64()*0.4 - 0.2 // [-0.2, 0.2]
	e.vy = e.rng.Float64()*0.4 - 0.2 // [-0.2, 0.2]
	e.angle = 0.0
	e.angularV = 0.0
	e.currentStep = 0
	e.crashed = false
	e.landed = false

	return e.GetObservations(), nil
}

// Step 执行一步
func (e *LunarLanderEnvironment) Step(ctx context.Context, actions []core.Action) ([]core.Observation, []float64, []bool, error) {
	if len(actions) == 0 {
		return nil, nil, nil, fmt.Errorf("no actions provided")
	}

	e.currentStep++

	// 解析动作（4个离散动作：0: 不动, 1: 左引擎, 2: 主引擎, 3: 右引擎）
	var actionValue int

	// 尝试从GenericAction中提取
	if genericAction, ok := actions[0].(*core.GenericAction); ok {
		actionFloat, err := genericAction.GetFloat64()
		if err != nil {
			return nil, nil, nil, fmt.Errorf("failed to extract action value: %w", err)
		}
		actionValue = int(actionFloat)
		if actionValue < 0 || actionValue > 3 {
			actionValue = 0 // 默认不动
		}
	} else if lunarAction, ok := actions[0].(*LunarLanderAction); ok {
		actionValue = lunarAction.Action
	} else {
		return nil, nil, nil, fmt.Errorf("unsupported action type: %T", actions[0])
	}

	// 物理仿真
	// 重力作用
	e.vy -= e.gravity * e.dt

	// 根据动作施加推力
	switch actionValue {
	case 1: // 左引擎
		e.vx -= e.lateralPower * e.dt
		e.angularV += 0.1
	case 2: // 主引擎
		e.vy += e.thrustPower * math.Cos(e.angle) * e.dt
		e.vx += e.thrustPower * math.Sin(e.angle) * e.dt
	case 3: // 右引擎
		e.vx += e.lateralPower * e.dt
		e.angularV -= 0.1
	}

	// 更新位置和角度
	e.x += e.vx * e.dt
	e.y += e.vy * e.dt
	e.angle += e.angularV * e.dt

	// 限制角度
	if e.angle > math.Pi {
		e.angle -= 2 * math.Pi
	} else if e.angle < -math.Pi {
		e.angle += 2 * math.Pi
	}

	// 检查碰撞和着陆
	if e.y <= e.landingPadY {
		if math.Abs(e.x-e.landingPadX) <= e.landingPadW/2 &&
			math.Abs(e.vx) < 0.5 && math.Abs(e.vy) < 0.5 &&
			math.Abs(e.angle) < 0.3 {
			e.landed = true
		} else {
			e.crashed = true
		}
	}

	// 检查是否超出边界
	if math.Abs(e.x) > 3.0 || e.y > 3.0 {
		e.crashed = true
	}

	// 计算奖励
	reward := e.calculateReward(actionValue)

	// 检查是否结束
	done := e.crashed || e.landed || e.currentStep >= e.maxSteps

	observations := e.GetObservations()
	rewards := []float64{reward}
	dones := []bool{done}

	return observations, rewards, dones, nil
}

// calculateReward 计算奖励
func (e *LunarLanderEnvironment) calculateReward(action int) float64 {
	reward := 0.0

	// 基础距离奖励（越接近着陆区越好）
	distance := math.Sqrt((e.x-e.landingPadX)*(e.x-e.landingPadX) + (e.y-e.landingPadY)*(e.y-e.landingPadY))
	reward -= distance * 0.3

	// 速度惩罚（速度越小越好）
	reward -= (math.Abs(e.vx) + math.Abs(e.vy)) * 0.3

	// 角度惩罚（保持直立）
	reward -= math.Abs(e.angle) * 0.5

	// 燃料使用惩罚
	if action == 1 || action == 3 {
		reward -= 0.03 // 侧推进器
	} else if action == 2 {
		reward -= 0.3 // 主推进器
	}

	// 着陆奖励
	if e.landed {
		reward += 100.0
	} else if e.crashed {
		reward -= 100.0
	}

	return reward
}

// GetObservations 获取当前观察
func (e *LunarLanderEnvironment) GetObservations() []core.Observation {
	// 观察：[x, y, vx, vy, angle, angular_v, leg1_contact, leg2_contact]
	// 简化版不考虑腿部接触，用0填充
	data := []float64{
		e.x,
		e.y,
		e.vx,
		e.vy,
		e.angle,
		e.angularV,
		0.0, // leg1_contact (简化为0)
		0.0, // leg2_contact (简化为0)
	}

	metadata := map[string]interface{}{
		"x":         e.x,
		"y":         e.y,
		"vx":        e.vx,
		"vy":        e.vy,
		"angle":     e.angle,
		"angular_v": e.angularV,
		"step":      e.currentStep,
		"max_steps": e.maxSteps,
		"crashed":   e.crashed,
		"landed":    e.landed,
	}

	observation := core.NewBaseObservation(data, metadata)
	return []core.Observation{observation}
}

// GetReward 计算奖励
func (e *LunarLanderEnvironment) GetReward() []float64 {
	reward := e.calculateReward(0) // 假设无动作的基础奖励
	return []float64{reward}
}

// Close 关闭环境
func (e *LunarLanderEnvironment) Close() error {
	return e.BaseEnvironment.Close()
}

// GetSpaces 获取LunarLander场景的动作空间和观察空间定义
func (e *LunarLanderEnvironment) GetSpaces() core.SpaceDefinition {
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

// LunarLanderAction LunarLander专用动作
type LunarLanderAction struct {
	Action int // 0: 不动, 1: 左引擎, 2: 主引擎, 3: 右引擎
}

// NewLunarLanderAction 创建新的LunarLander动作
func NewLunarLanderAction(action int) *LunarLanderAction {
	return &LunarLanderAction{Action: action}
}

// GetData 获取动作数据
func (a *LunarLanderAction) GetData() interface{} {
	return a.Action
}

// Validate 验证动作
func (a *LunarLanderAction) Validate() error {
	if a.Action < 0 || a.Action > 3 {
		return fmt.Errorf("lunarlander action must be 0-3, got %d", a.Action)
	}
	return nil
}
