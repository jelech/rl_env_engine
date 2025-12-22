package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/jelech/rl_env_engine/core"
	"github.com/jelech/rl_env_engine/scenarios/simple"
)

// GymAPI 定义Gym兼容的API结构
type GymAPI struct {
	engine       *core.SimulationEngine
	environments map[string]core.Environment
	configs      map[string]core.Config
}

// ResetRequest 重置请求
type ResetRequest struct {
	EnvID string `json:"env_id"`
}

// ResetResponse 重置响应
type ResetResponse struct {
	Observation [][]float64            `json:"observation"`
	Info        map[string]interface{} `json:"info"`
}

// StepRequest 步进请求
type StepRequest struct {
	EnvID  string                 `json:"env_id"`
	Action map[string]interface{} `json:"action"`
}

// StepResponse 步进响应
type StepResponse struct {
	Observation [][]float64            `json:"observation"`
	Reward      []float64              `json:"reward"`
	Done        []bool                 `json:"done"`
	Info        map[string]interface{} `json:"info"`
}

// CreateEnvRequest 创建环境请求
type CreateEnvRequest struct {
	EnvID    string                 `json:"env_id"`
	Scenario string                 `json:"scenario"`
	Config   map[string]interface{} `json:"config"`
}

// CreateEnvResponse 创建环境响应
type CreateEnvResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// InfoResponse 环境信息响应
type InfoResponse struct {
	Scenarios []string               `json:"scenarios"`
	EnvIDs    []string               `json:"env_ids"`
	Info      map[string]interface{} `json:"info"`
}

func NewGymAPI() *GymAPI {
	engine := core.NewSimulationEngine()

	// 注册简单测试场景
	simpleScenario := simple.NewSimpleScenario()
	engine.RegisterScenario(simpleScenario)

	return &GymAPI{
		engine:       engine,
		environments: make(map[string]core.Environment),
		configs:      make(map[string]core.Config),
	}
}

func (api *GymAPI) StartServer(port int) error {
	mux := http.NewServeMux()

	// 注册路由
	mux.HandleFunc("/", api.handleIndex)
	mux.HandleFunc("/info", api.handleInfo)
	mux.HandleFunc("/create", api.handleCreateEnv)
	mux.HandleFunc("/reset", api.handleReset)
	mux.HandleFunc("/step", api.handleStep)
	mux.HandleFunc("/close", api.handleClose)

	// 添加CORS中间件
	handler := api.corsMiddleware(mux)

	addr := fmt.Sprintf(":%d", port)
	log.Printf("Starting Gym API server on http://localhost%s", addr)
	log.Printf("Available endpoints:")
	log.Printf("  GET  /         - API information")
	log.Printf("  GET  /info     - Environment information")
	log.Printf("  POST /create   - Create environment")
	log.Printf("  POST /reset    - Reset environment")
	log.Printf("  POST /step     - Step environment")
	log.Printf("  POST /close    - Close environment")

	return http.ListenAndServe(addr, handler)
}

func (api *GymAPI) corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func (api *GymAPI) handleIndex(w http.ResponseWriter, r *http.Request) {
	info := map[string]interface{}{
		"name":        "Simulation Gym API",
		"version":     "1.0.0",
		"description": "OpenAI Gym compatible API for simulation environments",
		"endpoints": map[string]string{
			"GET /":        "This information",
			"GET /info":    "Get environment information",
			"POST /create": "Create a new environment",
			"POST /reset":  "Reset an environment",
			"POST /step":   "Step an environment",
			"POST /close":  "Close an environment",
		},
	}

	api.writeJSON(w, info)
}

func (api *GymAPI) handleInfo(w http.ResponseWriter, r *http.Request) {
	scenarios := api.engine.ListScenarios()
	envIDs := make([]string, 0, len(api.environments))
	for envID := range api.environments {
		envIDs = append(envIDs, envID)
	}

	response := InfoResponse{
		Scenarios: scenarios,
		EnvIDs:    envIDs,
		Info: map[string]interface{}{
			"total_scenarios":     len(scenarios),
			"active_environments": len(envIDs),
		},
	}

	api.writeJSON(w, response)
}

func (api *GymAPI) handleCreateEnv(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateEnvRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		api.writeError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// 检查环境是否已存在
	if _, exists := api.environments[req.EnvID]; exists {
		response := CreateEnvResponse{
			Success: false,
			Message: fmt.Sprintf("Environment %s already exists", req.EnvID),
		}
		api.writeJSON(w, response)
		return
	}

	// 创建配置
	config := core.NewBaseConfig(req.Config)

	// 创建环境
	env, err := api.engine.CreateEnvironment(req.Scenario, config)
	if err != nil {
		response := CreateEnvResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to create environment: %v", err),
		}
		api.writeJSON(w, response)
		return
	}

	// 保存环境和配置
	api.environments[req.EnvID] = env
	api.configs[req.EnvID] = config

	response := CreateEnvResponse{
		Success: true,
		Message: fmt.Sprintf("Environment %s created successfully", req.EnvID),
	}
	api.writeJSON(w, response)
}

func (api *GymAPI) handleReset(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req ResetRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		api.writeError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	env, exists := api.environments[req.EnvID]
	if !exists {
		api.writeError(w, fmt.Sprintf("Environment %s not found", req.EnvID), http.StatusNotFound)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	observations, err := env.Reset(ctx)
	if err != nil {
		api.writeError(w, fmt.Sprintf("Failed to reset environment: %v", err), http.StatusInternalServerError)
		return
	}

	// 转换观察为JSON格式
	obsData := make([][]float64, len(observations))
	for i, obs := range observations {
		obsData[i] = obs.GetData()
	}

	response := ResetResponse{
		Observation: obsData,
		Info:        env.GetInfo(),
	}

	api.writeJSON(w, response)
}

func (api *GymAPI) handleStep(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req StepRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		api.writeError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	env, exists := api.environments[req.EnvID]
	if !exists {
		api.writeError(w, fmt.Sprintf("Environment %s not found", req.EnvID), http.StatusNotFound)
		return
	}

	// 转换action为对应场景的Action类型
	actions, err := api.convertActions(req.Action)
	if err != nil {
		api.writeError(w, fmt.Sprintf("Failed to convert actions: %v", err), http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	observations, rewards, done, err := env.Step(ctx, actions)
	if err != nil {
		api.writeError(w, fmt.Sprintf("Failed to step environment: %v", err), http.StatusInternalServerError)
		return
	}

	// 转换观察为JSON格式
	obsData := make([][]float64, len(observations))
	for i, obs := range observations {
		obsData[i] = obs.GetData()
	}

	response := StepResponse{
		Observation: obsData,
		Reward:      rewards,
		Done:        done,
		Info:        env.GetInfo(),
	}

	api.writeJSON(w, response)
}

func (api *GymAPI) handleClose(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req struct {
		EnvID string `json:"env_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		api.writeError(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	env, exists := api.environments[req.EnvID]
	if !exists {
		api.writeError(w, fmt.Sprintf("Environment %s not found", req.EnvID), http.StatusNotFound)
		return
	}

	if err := env.Close(); err != nil {
		api.writeError(w, fmt.Sprintf("Failed to close environment: %v", err), http.StatusInternalServerError)
		return
	}

	delete(api.environments, req.EnvID)
	delete(api.configs, req.EnvID)

	response := map[string]interface{}{
		"success": true,
		"message": fmt.Sprintf("Environment %s closed successfully", req.EnvID),
	}

	api.writeJSON(w, response)
}

func (api *GymAPI) convertActions(actionData map[string]interface{}) ([]core.Action, error) {
	// 支持多种场景的action转换

	// 尝试解析为简单场景的action
	if value, ok := actionData["value"]; ok {
		if val, ok := value.(float64); ok {
			action := simple.NewSimpleAction(val)
			return []core.Action{action}, nil
		} else {
			return nil, fmt.Errorf("invalid value type for simple action")
		}
	}

	return nil, fmt.Errorf("unsupported action format, expected 'sku_actions' or 'value' field")
}

func (api *GymAPI) writeJSON(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("Failed to encode JSON: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
	}
}

func (api *GymAPI) writeError(w http.ResponseWriter, message string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	response := map[string]interface{}{
		"error":   true,
		"message": message,
		"code":    code,
	}
	json.NewEncoder(w).Encode(response)
}
