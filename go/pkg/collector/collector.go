package collector

import (
	"context"
	"fmt"
	"log"
	"sync"
	"sync/atomic"
	"time"

	"github.com/jelech/rl_env_engine/go/pkg/core"
	"github.com/jelech/rl_env_engine/go/pkg/weightsync"
)

// WorkerClient 表示与一个仿真 worker 的连接
type WorkerClient interface {
	Reset(ctx context.Context) ([]float32, error)
	Step(ctx context.Context, actions []float32) (obs []float32, reward float32, done bool, err error)
	Close() error
}

// InferenceFunc 推理函数签名：输入 observation，返回 action, log_prob, value
type InferenceFunc func(obs []float32) (action []float32, logProb float32, value float32, err error)

// CollectorConfig 配置
type CollectorConfig struct {
	ID               string
	NumWorkers       int
	WeightSyncerURL  string
	ModelKey         string
	MaxEpisodeSteps  int
	S3UploadEnabled  bool
	S3Bucket         string
}

// Collector 驱动仿真 worker 采集 trajectory 数据
type Collector struct {
	config  CollectorConfig
	workers []WorkerClient
	syncer  *weightsync.RedisSyncer
	infer   InferenceFunc

	currentVersion atomic.Int64
	mu             sync.Mutex
	stats          CollectorStats
}

// CollectorStats 运行统计
type CollectorStats struct {
	EpisodesCompleted int64
	TotalSteps        int64
	TotalReward       float64
	WeightVersion     int64
}

// NewCollector 创建 Collector 实例
func NewCollector(config CollectorConfig, workers []WorkerClient, infer InferenceFunc) (*Collector, error) {
	c := &Collector{
		config:  config,
		workers: workers,
		infer:   infer,
	}

	if config.WeightSyncerURL != "" {
		syncer, err := weightsync.NewRedisSyncer(config.WeightSyncerURL, "rl")
		if err != nil {
			return nil, fmt.Errorf("failed to create weight syncer: %w", err)
		}
		c.syncer = syncer
	}

	return c, nil
}

// WaitForVersion 等待权重版本达到指定值（sync barrier）
func (c *Collector) WaitForVersion(ctx context.Context, targetVersion int64) error {
	if c.currentVersion.Load() >= targetVersion {
		return nil
	}

	if c.syncer == nil {
		return fmt.Errorf("no weight syncer configured")
	}

	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			ver, err := c.syncer.GetVersion(ctx, c.config.ModelKey)
			if err != nil {
				log.Printf("collector %s: failed to check version: %v", c.config.ID, err)
				continue
			}
			if ver >= targetVersion {
				c.currentVersion.Store(ver)
				return nil
			}
		}
	}
}

// Collect 使用当前权重执行一轮采集，每个 worker 跑一个 episode
func (c *Collector) Collect(ctx context.Context) ([]*core.Trajectory, error) {
	var wg sync.WaitGroup
	trajectories := make([]*core.Trajectory, len(c.workers))
	errs := make([]error, len(c.workers))

	for i, worker := range c.workers {
		wg.Add(1)
		go func(idx int, w WorkerClient) {
			defer wg.Done()
			traj, err := c.collectOneEpisode(ctx, w)
			trajectories[idx] = traj
			errs[idx] = err
		}(i, worker)
	}

	wg.Wait()

	var result []*core.Trajectory
	for i, traj := range trajectories {
		if errs[i] != nil {
			log.Printf("collector %s: worker %d error: %v", c.config.ID, i, errs[i])
			continue
		}
		if traj != nil {
			result = append(result, traj)
		}
	}

	c.mu.Lock()
	c.stats.EpisodesCompleted += int64(len(result))
	c.stats.WeightVersion = c.currentVersion.Load()
	c.mu.Unlock()

	return result, nil
}

func (c *Collector) collectOneEpisode(ctx context.Context, worker WorkerClient) (*core.Trajectory, error) {
	traj := core.AcquireTrajectory()

	obs, err := worker.Reset(ctx)
	if err != nil {
		core.ReleaseTrajectory(traj)
		return nil, fmt.Errorf("reset failed: %w", err)
	}

	maxSteps := c.config.MaxEpisodeSteps
	if maxSteps <= 0 {
		maxSteps = 100
	}

	var episodeReward float32

	for step := 0; step < maxSteps; step++ {
		select {
		case <-ctx.Done():
			core.ReleaseTrajectory(traj)
			return nil, ctx.Err()
		default:
		}

		action, logProb, value, err := c.infer(obs)
		if err != nil {
			core.ReleaseTrajectory(traj)
			return nil, fmt.Errorf("inference failed at step %d: %w", step, err)
		}

		nextObs, reward, done, err := worker.Step(ctx, action)
		if err != nil {
			core.ReleaseTrajectory(traj)
			return nil, fmt.Errorf("step failed at step %d: %w", step, err)
		}

		traj.AddTransition(core.Transition{
			State:     obs,
			Action:    action,
			Reward:    reward,
			NextState: nextObs,
			Done:      done,
			LogProb:   logProb,
			Value:     value,
		})

		episodeReward += reward

		c.mu.Lock()
		c.stats.TotalSteps++
		c.stats.TotalReward += float64(reward)
		c.mu.Unlock()

		if done {
			break
		}

		obs = nextObs
	}

	traj.EpisodeReward = episodeReward
	return traj, nil
}

// StartWeightSubscription 启动后台权重订阅
// 收到新版本通知后自动拉取权重并调用 onUpdate 回调
func (c *Collector) StartWeightSubscription(ctx context.Context, onUpdate func(data *weightsync.WeightData)) error {
	if c.syncer == nil {
		return fmt.Errorf("no weight syncer configured")
	}

	ch, err := c.syncer.Subscribe(ctx, c.config.ModelKey)
	if err != nil {
		return fmt.Errorf("failed to subscribe: %w", err)
	}

	go func() {
		for update := range ch {
			if update.Version <= c.currentVersion.Load() {
				continue
			}

			data, err := c.syncer.GetWeights(ctx, c.config.ModelKey)
			if err != nil {
				log.Printf("collector %s: failed to fetch weights v%d: %v", c.config.ID, update.Version, err)
				continue
			}
			if data == nil {
				continue
			}

			c.currentVersion.Store(data.Version)
			log.Printf("collector %s: updated to weight version %d", c.config.ID, data.Version)

			if onUpdate != nil {
				onUpdate(data)
			}
		}
	}()

	return nil
}

// GetStats 返回运行统计
func (c *Collector) GetStats() CollectorStats {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.stats
}

// Close 清理资源
func (c *Collector) Close() error {
	for _, w := range c.workers {
		if err := w.Close(); err != nil {
			log.Printf("collector %s: worker close error: %v", c.config.ID, err)
		}
	}
	if c.syncer != nil {
		return c.syncer.Close()
	}
	return nil
}
