package core

// GenericConfig 通用配置实现
type GenericConfig struct {
	*BaseConfig
}

// NewGenericConfig 创建一个新的通用配置
func NewGenericConfig(values map[string]interface{}) *GenericConfig {
	cfg := &GenericConfig{
		BaseConfig: NewBaseConfig(),
	}
	for k, v := range values {
		cfg.SetValue(k, v)
	}
	return cfg
}
