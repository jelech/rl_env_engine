package core

import (
	"testing"
)

func TestTrajectoryPool(t *testing.T) {
	traj := AcquireTrajectory()
	if traj == nil {
		t.Fatal("AcquireTrajectory returned nil")
	}
	if traj.Length() != 0 {
		t.Errorf("expected empty trajectory, got length %d", traj.Length())
	}

	traj.AddTransition(Transition{
		State:  []float32{1.0, 2.0},
		Action: []float32{0.5},
		Reward: 1.0,
		Done:   false,
	})

	if traj.Length() != 1 {
		t.Errorf("expected length 1, got %d", traj.Length())
	}

	ReleaseTrajectory(traj)

	traj2 := AcquireTrajectory()
	if traj2.Length() != 0 {
		t.Errorf("expected reset trajectory, got length %d", traj2.Length())
	}
	ReleaseTrajectory(traj2)
}

func TestFloat32SlicePool(t *testing.T) {
	s := AcquireFloat32Slice(16)
	if len(s) != 16 {
		t.Errorf("expected slice of length 16, got %d", len(s))
	}
	ReleaseFloat32Slice(s)

	s2 := AcquireFloat32Slice(8)
	if len(s2) != 8 {
		t.Errorf("expected slice of length 8, got %d", len(s2))
	}
	ReleaseFloat32Slice(s2)
}

func TestTrajectoryReset(t *testing.T) {
	traj := &Trajectory{
		EnvID:         "test-env",
		EpisodeReward: 10.0,
		Transitions:   make([]Transition, 0, 64),
	}

	traj.AddTransition(Transition{
		State:  []float32{1.0},
		Action: []float32{0.0},
		Reward: 5.0,
		Done:   false,
	})

	traj.Reset()

	if traj.EnvID != "" {
		t.Errorf("expected empty EnvID after reset, got %q", traj.EnvID)
	}
	if traj.EpisodeReward != 0 {
		t.Errorf("expected 0 reward after reset, got %f", traj.EpisodeReward)
	}
	if traj.Length() != 0 {
		t.Errorf("expected 0 length after reset, got %d", traj.Length())
	}
}
