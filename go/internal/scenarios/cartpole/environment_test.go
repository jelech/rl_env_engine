package cartpole

import (
	"context"
	"testing"

	"github.com/jelech/rl_env_engine/go/pkg/core"
)

func TestCartPoleEnvironmentReset(t *testing.T) {
	config := core.NewBaseConfig(map[string]interface{}{"max_steps": 500})
	env := NewCartPoleEnvironment(config)

	obs, err := env.Reset(context.Background())
	if err != nil {
		t.Fatalf("Reset failed: %v", err)
	}
	if len(obs) != 1 {
		t.Fatalf("expected 1 observation, got %d", len(obs))
	}
	if len(obs[0].GetData()) != 4 {
		t.Fatalf("expected observation dim=4, got %d", len(obs[0].GetData()))
	}
}

func TestCartPoleEnvironmentStep(t *testing.T) {
	config := core.NewBaseConfig(map[string]interface{}{"max_steps": 500})
	env := NewCartPoleEnvironment(config)

	_, err := env.Reset(context.Background())
	if err != nil {
		t.Fatalf("Reset failed: %v", err)
	}

	action := NewCartPoleAction(1)
	obs, rewards, done, err := env.Step(context.Background(), []core.Action{action})
	if err != nil {
		t.Fatalf("Step failed: %v", err)
	}
	if len(obs) != 1 {
		t.Fatalf("expected 1 observation, got %d", len(obs))
	}
	if len(rewards) != 1 {
		t.Fatalf("expected 1 reward, got %d", len(rewards))
	}
	if len(done) != 1 {
		t.Fatalf("expected 1 done, got %d", len(done))
	}
	if rewards[0] != 1.0 {
		t.Errorf("expected reward 1.0, got %f", rewards[0])
	}
}

func TestCartPoleEnvironmentEpisode(t *testing.T) {
	config := core.NewBaseConfig(map[string]interface{}{"max_steps": 100})
	env := NewCartPoleEnvironment(config)

	_, err := env.Reset(context.Background())
	if err != nil {
		t.Fatalf("Reset failed: %v", err)
	}

	totalReward := 0.0
	for i := 0; i < 200; i++ {
		actionVal := i % 2
		action := NewCartPoleAction(actionVal)
		_, rewards, dones, err := env.Step(context.Background(), []core.Action{action})
		if err != nil {
			t.Fatalf("Step %d failed: %v", i, err)
		}
		totalReward += rewards[0]
		if dones[0] {
			break
		}
	}

	if totalReward == 0 {
		t.Error("expected non-zero total reward")
	}
}

func TestCartPoleGetSpaces(t *testing.T) {
	config := core.NewBaseConfig(nil)
	env := NewCartPoleEnvironment(config)

	spaces := env.GetSpaces()
	if spaces.ActionSpace.Type != core.SpaceTypeDiscrete {
		t.Errorf("expected discrete action space, got %d", spaces.ActionSpace.Type)
	}
	if len(spaces.ObservationSpace.Shape) != 1 || spaces.ObservationSpace.Shape[0] != 4 {
		t.Errorf("expected obs shape [4], got %v", spaces.ObservationSpace.Shape)
	}
}
