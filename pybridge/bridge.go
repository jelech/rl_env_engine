package pybridge

import (
	"context"
	"encoding/json"
	"sync"
	"unsafe"

	"github.com/jelech/rl_env_engine/core"
)

var (
	// Registry 存储已注册的场景 (Scenarios)
	Registry = make(map[string]core.Scenario)
	// Envs 存储活跃的环境实例
	Envs   = make(map[int]core.Environment)
	envMu  sync.RWMutex
	nextID = 1

	// LastObs 存储每个环境最后一步的观测值 (序列化为平铺的 float64 数组)
	// 这是一种将数据传回 C/Python 的简单方式，避免复杂的内存管理
	LastObs     = make(map[int][]float64)
	LastRewards = make(map[int][]float64)
	LastDones   = make(map[int][]bool)
)

// Register 注册一个场景
func Register(s core.Scenario) {
	Registry[s.GetName()] = s
}

// CreateEnv 创建一个新的环境实例
func CreateEnv(scenarioName string, configJson string) int {
	// 查找场景
	s, ok := Registry[scenarioName]
	if !ok {
		return -1 // 场景未找到
	}

	// 解析配置 JSON
	var cfgMap map[string]interface{}
	if err := json.Unmarshal([]byte(configJson), &cfgMap); err != nil {
		return -2 // JSON 解析错误
	}

	// 创建环境
	env, err := s.CreateEnvironment(core.NewBaseConfig(cfgMap))
	if err != nil {
		return -3 // 创建失败
	}

	envMu.Lock()
	defer envMu.Unlock()
	id := nextID
	nextID++
	Envs[id] = env
	return id
}

// Reset 重置环境
func Reset(id int) int {
	envMu.RLock()
	env, ok := Envs[id]
	envMu.RUnlock()
	if !ok {
		return -1 // 环境 ID 无效
	}

	obs, err := env.Reset(context.Background())
	if err != nil {
		return -2 // 重置失败
	}

	// 缓存观测值 (平铺)
	// 假设目前是单智能体/单观测，或者是所有观测的平铺
	// 对于 CacheRL，它返回每个 SKU 的观测列表
	// 我们需要将其平铺为单个 float 数组供 Python 使用
	flattened := FlattenObservations(obs)

	envMu.Lock()
	LastObs[id] = flattened
	envMu.Unlock()

	return len(flattened)
}

// Step 执行一步环境仿真
func Step(id int, actionData []float64) int {
	envMu.RLock()
	env, ok := Envs[id]
	envMu.RUnlock()
	if !ok {
		return -1 // 环境 ID 无效
	}

	// 构造 Action
	// 由于 Core 的 Action 接口比较通用，这里我们假设使用 GenericAction
	// CacheRL 环境的实现 (env.go) 已经支持识别 core.GenericAction
	var actions []core.Action
	act := core.NewGenericAction(actionData)
	actions = append(actions, act)

	// 执行 Step
	obs, rewards, dones, err := env.Step(context.Background(), actions)
	if err != nil {
		return -2 // Step 执行失败
	}

	flattenedObs := FlattenObservations(obs)
	flattenedRewards := rewards

	envMu.Lock()
	LastObs[id] = flattenedObs
	LastRewards[id] = flattenedRewards
	LastDones[id] = dones
	envMu.Unlock()

	return 0 // 成功
}

// GetObservation 将观测数据复制到 C 指针指向的内存
func GetObservation(id int, dest unsafe.Pointer, maxLen int) int {
	envMu.RLock()
	data, ok := LastObs[id]
	envMu.RUnlock()
	if !ok {
		return 0
	}

	return copyToC(data, dest, maxLen)
}

// GetReward 将奖励数据复制到 C 指针指向的内存
func GetReward(id int, dest unsafe.Pointer, maxLen int) int {
	envMu.RLock()
	data, ok := LastRewards[id]
	envMu.RUnlock()
	if !ok {
		return 0
	}
	return copyToC(data, dest, maxLen)
}

// GetDone 将 Done (结束标志) 数据复制到 C 指针指向的内存
// 注意：C/Python 端通常期望 bool 为 byte (0/1) 或 int
// 这里我们将其转换为 byte (char) 数组
func GetDone(id int, dest unsafe.Pointer, maxLen int) int {
	envMu.RLock()
	data, ok := LastDones[id]
	envMu.RUnlock()
	if !ok {
		return 0
	}

	// 将 bool 转换为 byte (char) 1/0
	// 这是一个比较 hacky 的 unsafe 转换，但对于 CGo 是高效的
	// 假设 dest 是一个足够大的 byte 数组
	cArray := (*[1 << 30]byte)(dest)
	count := len(data)
	if count > maxLen {
		count = maxLen
	}
	for i := 0; i < count; i++ {
		if data[i] {
			cArray[i] = 1
		} else {
			cArray[i] = 0
		}
	}
	return count
}

// FlattenObservations 辅助函数：将观测对象列表平铺为 float64 数组
func FlattenObservations(obs []core.Observation) []float64 {
	var flat []float64
	for _, o := range obs {
		flat = append(flat, o.GetData()...)
	}
	return flat
}

// copyToC 辅助函数：将 float64 切片复制到 C double 数组
func copyToC(src []float64, dest unsafe.Pointer, maxLen int) int {
	if len(src) == 0 {
		return 0
	}

	// 我们将 dest 视为 *float64 (C double 数组)
	// 使用 unsafe 将 C 指针转换为 Go 的大数组指针以便索引访问
	cArray := (*[1 << 30]float64)(dest)
	count := len(src)
	if count > maxLen {
		count = maxLen
	}
	for i := 0; i < count; i++ {
		cArray[i] = src[i]
	}
	return count
}

// CloseEnv 关闭并移除环境实例
func CloseEnv(id int) {
	envMu.Lock()
	delete(Envs, id)
	delete(LastObs, id)
	delete(LastRewards, id)
	delete(LastDones, id)
	envMu.Unlock()
}
