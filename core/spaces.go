package core

// SpaceType 定义空间类型
type SpaceType int

const (
	SpaceTypeBox SpaceType = iota
	SpaceTypeDiscrete
	SpaceTypeMultiDiscrete
	SpaceTypeMultiBinary
)

// ActionSpace 定义动作空间
type ActionSpace struct {
	Type  SpaceType
	Low   []float64
	High  []float64
	Shape []int32
	Dtype string
}

// ObservationSpace 定义观察空间
type ObservationSpace struct {
	Type  SpaceType
	Low   []float64
	High  []float64
	Shape []int32
	Dtype string
}

// SpaceDefinition 包含动作空间和观察空间的定义
type SpaceDefinition struct {
	ActionSpace      ActionSpace
	ObservationSpace ObservationSpace
}
