package collector

import "sort"

// SKUProfile 描述单个 SKU 的计算复杂度
type SKUProfile struct {
	ID         string
	Complexity float64 // 预估的单步耗时 (μs)，由 profiling pass 得到
}

// WorkerAssignment 描述一个 worker 分配到的 SKU 列表
type WorkerAssignment struct {
	WorkerID string
	SKUs     []string
	TotalLoad float64
}

// DistributeSKUs 使用 round-robin by complexity 将 SKU 分配到 N 个 worker
// 先按复杂度降序排列，然后轮流分配给当前负载最轻的 worker（贪心调度）
func DistributeSKUs(profiles []SKUProfile, numWorkers int) []WorkerAssignment {
	if numWorkers <= 0 {
		return nil
	}

	sort.Slice(profiles, func(i, j int) bool {
		return profiles[i].Complexity > profiles[j].Complexity
	})

	assignments := make([]WorkerAssignment, numWorkers)
	for i := range assignments {
		assignments[i].SKUs = make([]string, 0, len(profiles)/numWorkers+1)
	}

	for _, p := range profiles {
		minIdx := 0
		for i := 1; i < numWorkers; i++ {
			if assignments[i].TotalLoad < assignments[minIdx].TotalLoad {
				minIdx = i
			}
		}
		assignments[minIdx].SKUs = append(assignments[minIdx].SKUs, p.ID)
		assignments[minIdx].TotalLoad += p.Complexity
	}

	return assignments
}

// DistributeRoundRobin 简单的 round-robin 按复杂度交替分配
// 适合无 profiling 数据的场景，将"重"和"轻"的 SKU 交替打散
func DistributeRoundRobin(profiles []SKUProfile, numWorkers int) []WorkerAssignment {
	if numWorkers <= 0 {
		return nil
	}

	sort.Slice(profiles, func(i, j int) bool {
		return profiles[i].Complexity > profiles[j].Complexity
	})

	assignments := make([]WorkerAssignment, numWorkers)
	for i := range assignments {
		assignments[i].SKUs = make([]string, 0, len(profiles)/numWorkers+1)
	}

	for i, p := range profiles {
		idx := i % numWorkers
		assignments[idx].SKUs = append(assignments[idx].SKUs, p.ID)
		assignments[idx].TotalLoad += p.Complexity
	}

	return assignments
}

// DistributeUniform 均匀分配（忽略复杂度差异），适合 SKU 间差异不大的场景
func DistributeUniform(skuIDs []string, numWorkers int) []WorkerAssignment {
	if numWorkers <= 0 {
		return nil
	}

	assignments := make([]WorkerAssignment, numWorkers)
	for i := range assignments {
		assignments[i].SKUs = make([]string, 0, len(skuIDs)/numWorkers+1)
	}

	for i, id := range skuIDs {
		idx := i % numWorkers
		assignments[idx].SKUs = append(assignments[idx].SKUs, id)
	}

	return assignments
}
