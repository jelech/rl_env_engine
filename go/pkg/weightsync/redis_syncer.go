package weightsync

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strconv"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

// WeightData 表示带版本号的模型权重
type WeightData struct {
	Version   int64             `json:"version"`
	Data      []byte            `json:"data"`
	ModelKey  string            `json:"model_key"`
	Format    string            `json:"format"`
	Timestamp int64             `json:"timestamp"`
	Metadata  map[string]string `json:"metadata,omitempty"`
}

// RedisSyncer 基于 Redis 的权重同步器
// 使用 pub/sub + 版本号实现权重的分发
type RedisSyncer struct {
	client *redis.Client
	prefix string
	mu     sync.RWMutex
}

// NewRedisSyncer 创建 Redis 权重同步器
func NewRedisSyncer(redisURL string, prefix string) (*RedisSyncer, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("invalid redis URL: %w", err)
	}

	client := redis.NewClient(opts)
	if prefix == "" {
		prefix = "rl"
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis ping failed: %w", err)
	}

	return &RedisSyncer{
		client: client,
		prefix: prefix,
	}, nil
}

func (r *RedisSyncer) weightKey(modelKey string) string {
	return fmt.Sprintf("%s:weights:%s", r.prefix, modelKey)
}

func (r *RedisSyncer) versionKey(modelKey string) string {
	return fmt.Sprintf("%s:version:%s", r.prefix, modelKey)
}

func (r *RedisSyncer) channelKey(modelKey string) string {
	return fmt.Sprintf("%s:updates:%s", r.prefix, modelKey)
}

// SetWeights 上传新版本权重并通知所有订阅者
// 使用 Pipeline 批量执行: SET weight + SET version + PUBLISH
func (r *RedisSyncer) SetWeights(ctx context.Context, key string, data *WeightData) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal weight data: %w", err)
	}

	pipe := r.client.Pipeline()
	pipe.Set(ctx, r.weightKey(key), jsonData, 0)
	pipe.Set(ctx, r.versionKey(key), data.Version, 0)
	pipe.Publish(ctx, r.channelKey(key), strconv.FormatInt(data.Version, 10))
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("failed to set weights: %w", err)
	}

	return nil
}

// GetWeights 获取指定 model key 的最新权重
func (r *RedisSyncer) GetWeights(ctx context.Context, key string) (*WeightData, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	jsonData, err := r.client.Get(ctx, r.weightKey(key)).Bytes()
	if err != nil {
		if err == redis.Nil {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to get weights: %w", err)
	}

	var data WeightData
	if err := json.Unmarshal(jsonData, &data); err != nil {
		return nil, fmt.Errorf("failed to unmarshal weight data: %w", err)
	}

	return &data, nil
}

// GetVersion 获取当前最新版本号
func (r *RedisSyncer) GetVersion(ctx context.Context, key string) (int64, error) {
	val, err := r.client.Get(ctx, r.versionKey(key)).Int64()
	if err != nil {
		if err == redis.Nil {
			return 0, nil
		}
		return 0, fmt.Errorf("failed to get version: %w", err)
	}
	return val, nil
}

// VersionUpdate 表示来自 pub/sub 的版本更新通知
type VersionUpdate struct {
	Version  int64
	ModelKey string
}

// Subscribe 订阅权重更新通知
// 返回一个 channel，每当 learner 推送新版本时，通过 channel 发送版本号
// 调用 cancel 函数或 ctx 过期时停止订阅
func (r *RedisSyncer) Subscribe(ctx context.Context, key string) (<-chan VersionUpdate, error) {
	pubsub := r.client.Subscribe(ctx, r.channelKey(key))

	_, err := pubsub.Receive(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to subscribe: %w", err)
	}

	ch := make(chan VersionUpdate, 16)

	go func() {
		defer close(ch)
		defer pubsub.Close()

		msgCh := pubsub.Channel()
		for {
			select {
			case <-ctx.Done():
				return
			case msg, ok := <-msgCh:
				if !ok {
					return
				}
				version, err := strconv.ParseInt(msg.Payload, 10, 64)
				if err != nil {
					log.Printf("weightsync: invalid version payload: %s", msg.Payload)
					continue
				}
				select {
				case ch <- VersionUpdate{Version: version, ModelKey: key}:
				default:
					log.Printf("weightsync: update channel full, dropping version %d", version)
				}
			}
		}
	}()

	return ch, nil
}

// Close 关闭 Redis 连接
func (r *RedisSyncer) Close() error {
	return r.client.Close()
}
