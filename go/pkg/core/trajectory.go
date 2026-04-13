package core

import "sync"

// Transition 表示仿真中的一个步骤转换
type Transition struct {
	State    []float32
	Action   []float32
	Reward   float32
	NextState []float32
	Done     bool
	LogProb  float32
	Value    float32
}

// Trajectory 表示一个完整 episode 的轨迹数据
type Trajectory struct {
	EnvID         string
	Transitions   []Transition
	EpisodeReward float32
}

// Reset 重置 trajectory 以便复用，保留底层切片容量
func (t *Trajectory) Reset() {
	t.EnvID = ""
	t.EpisodeReward = 0
	t.Transitions = t.Transitions[:0]
}

// AddTransition 追加一个 transition
func (t *Trajectory) AddTransition(tr Transition) {
	t.Transitions = append(t.Transitions, tr)
}

// Length 返回步数
func (t *Trajectory) Length() int {
	return len(t.Transitions)
}

// TrajectoryPool 使用 sync.Pool 复用 Trajectory 对象，减少 GC 压力
var TrajectoryPool = sync.Pool{
	New: func() interface{} {
		return &Trajectory{
			Transitions: make([]Transition, 0, 128),
		}
	},
}

// AcquireTrajectory 从对象池获取一个 Trajectory
func AcquireTrajectory() *Trajectory {
	t := TrajectoryPool.Get().(*Trajectory)
	t.Reset()
	return t
}

// ReleaseTrajectory 将 Trajectory 归还对象池
func ReleaseTrajectory(t *Trajectory) {
	if t == nil {
		return
	}
	t.Reset()
	TrajectoryPool.Put(t)
}

// TransitionPool 复用 float32 切片，用于高频的状态/动作数据
var float32SlicePool = sync.Pool{
	New: func() interface{} {
		s := make([]float32, 0, 32)
		return &s
	},
}

// AcquireFloat32Slice 从对象池获取一个 float32 切片
func AcquireFloat32Slice(size int) []float32 {
	sp := float32SlicePool.Get().(*[]float32)
	s := *sp
	if cap(s) >= size {
		s = s[:size]
	} else {
		s = make([]float32, size)
	}
	return s
}

// ReleaseFloat32Slice 将 float32 切片归还对象池
func ReleaseFloat32Slice(s []float32) {
	s = s[:0]
	float32SlicePool.Put(&s)
}
