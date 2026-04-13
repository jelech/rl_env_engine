package collector

import (
	"testing"
)

func TestDistributeSKUs(t *testing.T) {
	profiles := []SKUProfile{
		{ID: "a", Complexity: 10},
		{ID: "b", Complexity: 8},
		{ID: "c", Complexity: 6},
		{ID: "d", Complexity: 4},
		{ID: "e", Complexity: 2},
	}

	assignments := DistributeSKUs(profiles, 2)
	if len(assignments) != 2 {
		t.Fatalf("expected 2 assignments, got %d", len(assignments))
	}

	totalSKUs := 0
	for _, a := range assignments {
		totalSKUs += len(a.SKUs)
	}
	if totalSKUs != 5 {
		t.Errorf("expected 5 total SKUs, got %d", totalSKUs)
	}

	loadDiff := assignments[0].TotalLoad - assignments[1].TotalLoad
	if loadDiff < 0 {
		loadDiff = -loadDiff
	}
	if loadDiff > 10 {
		t.Errorf("load imbalance too large: %.1f vs %.1f", assignments[0].TotalLoad, assignments[1].TotalLoad)
	}
}

func TestDistributeRoundRobin(t *testing.T) {
	profiles := []SKUProfile{
		{ID: "a", Complexity: 10},
		{ID: "b", Complexity: 5},
		{ID: "c", Complexity: 3},
		{ID: "d", Complexity: 1},
	}

	assignments := DistributeRoundRobin(profiles, 3)
	if len(assignments) != 3 {
		t.Fatalf("expected 3 assignments, got %d", len(assignments))
	}

	totalSKUs := 0
	for _, a := range assignments {
		totalSKUs += len(a.SKUs)
	}
	if totalSKUs != 4 {
		t.Errorf("expected 4 total SKUs, got %d", totalSKUs)
	}
}

func TestDistributeUniform(t *testing.T) {
	skus := []string{"a", "b", "c", "d", "e"}
	assignments := DistributeUniform(skus, 2)
	if len(assignments) != 2 {
		t.Fatalf("expected 2 assignments, got %d", len(assignments))
	}

	totalSKUs := 0
	for _, a := range assignments {
		totalSKUs += len(a.SKUs)
	}
	if totalSKUs != 5 {
		t.Errorf("expected 5 total SKUs, got %d", totalSKUs)
	}
}

func TestDistributeEdgeCases(t *testing.T) {
	result := DistributeSKUs(nil, 0)
	if result != nil {
		t.Error("expected nil for 0 workers")
	}

	result = DistributeUniform(nil, 0)
	if result != nil {
		t.Error("expected nil for 0 workers with uniform")
	}

	single := DistributeSKUs([]SKUProfile{{ID: "x", Complexity: 5}}, 3)
	if len(single) != 3 {
		t.Fatalf("expected 3 assignments, got %d", len(single))
	}
	totalSKUs := 0
	for _, a := range single {
		totalSKUs += len(a.SKUs)
	}
	if totalSKUs != 1 {
		t.Errorf("expected 1 total SKU, got %d", totalSKUs)
	}
}
