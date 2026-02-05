package server

import (
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"time"

	"github.com/jelech/rl_env_engine/go/internal/scenarios/simple"
	"github.com/jelech/rl_env_engine/go/pkg/core"
)

// HandleStepBinary handles binary step requests
// It supports raw-bytes encoding for high performance
func (api *GymAPI) handleStepBinary(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 1. Check encoding
	encoding := r.Header.Get("X-Data-Encoding")
	envID := r.Header.Get("X-Env-ID")

	if envID == "" {
		http.Error(w, "X-Env-ID header required", http.StatusBadRequest)
		return
	}

	env, exists := api.environments[envID]
	if !exists {
		http.Error(w, fmt.Sprintf("Environment %s not found", envID), http.StatusNotFound)
		return
	}

	var actions []core.Action
	var err error

	// 2. Parse body based on encoding
	switch encoding {
	case "raw-bytes", "raw-float32":
		// Read raw bytes
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read body", http.StatusBadRequest)
			return
		}

		// Convert bytes to float32 array
		// Assuming LittleEndian float32 array
		values := bytesToFloat32s(body)

		// For simple scenario, we just take the first value
		// In a real scenario, we would map this array to the action space
		if len(values) > 0 {
			// Create action from the first value (simplified for demo)
			action := simple.NewSimpleAction(float64(values[0]))
			actions = []core.Action{action}
		} else {
			http.Error(w, "Empty action data", http.StatusBadRequest)
			return
		}

	case "json":
		// Fallback to JSON parsing
		var req StepRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid JSON", http.StatusBadRequest)
			return
		}
		actions, err = api.convertActions(req.Action)
		if err != nil {
			http.Error(w, fmt.Sprintf("Failed to convert actions: %v", err), http.StatusBadRequest)
			return
		}

	default:
		http.Error(w, fmt.Sprintf("Unsupported encoding: %s", encoding), http.StatusUnsupportedMediaType)
		return
	}

	// 3. Step environment
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	observations, rewards, done, err := env.Step(ctx, actions)
	if err != nil {
		http.Error(w, fmt.Sprintf("Failed to step environment: %v", err), http.StatusInternalServerError)
		return
	}

	// 4. Return binary response
	// We return raw float32 array: [obs_len, obs_data..., reward_len, reward_data..., done_byte]
	// This is a simple custom binary protocol

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("X-Data-Encoding", "raw-float32")

	// Serialize response
	// Simplified: just return the first observation data
	if len(observations) > 0 {
		obsData := observations[0].GetData()

		// Convert float64 obs to float32 bytes
		respBytes := float64sToBytes(obsData)

		// Append reward (as float32)
		if len(rewards) > 0 {
			rewardBytes := float64sToBytes(rewards)
			respBytes = append(respBytes, rewardBytes...)
		}

		// Append done (as byte)
		if len(done) > 0 {
			doneBytes := boolToBytes(done[0])
			respBytes = append(respBytes, doneBytes...)
		}

		w.Write(respBytes)
	}
}

func bytesToFloat32s(b []byte) []float32 {
	if len(b)%4 != 0 {
		return nil
	}

	count := len(b) / 4
	result := make([]float32, count)

	for i := 0; i < count; i++ {
		bits := binary.LittleEndian.Uint32(b[i*4 : (i+1)*4])
		result[i] = math.Float32frombits(bits)
	}

	return result
}

func float64sToBytes(f []float64) []byte {
	result := make([]byte, len(f)*4)
	for i, v := range f {
		bits := math.Float32bits(float32(v))
		binary.LittleEndian.PutUint32(result[i*4:(i+1)*4], bits)
	}
	return result
}

func boolToBytes(b bool) []byte {
	if b {
		return []byte{1}
	}
	return []byte{0}
}
