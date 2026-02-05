package core

import (
	"fmt"
	"reflect"
)

// GenericAction 通用的Action实现，可以承载任何类型的数据
type GenericAction struct {
	data interface{}
}

// NewGenericAction 创建一个新的通用Action
func NewGenericAction(data interface{}) *GenericAction {
	return &GenericAction{data: data}
}

// GetData 获取Action的数据
func (a *GenericAction) GetData() interface{} {
	return a.data
}

// Validate 验证Action的有效性
func (a *GenericAction) Validate() error {
	if a.data == nil {
		return fmt.Errorf("action data is nil")
	}
	return nil
}

// GetFloat64 尝试将数据转换为float64
func (a *GenericAction) GetFloat64() (float64, error) {
	switch v := a.data.(type) {
	case float64:
		return v, nil
	case float32:
		return float64(v), nil
	case int:
		return float64(v), nil
	case int64:
		return float64(v), nil
	case int32:
		return float64(v), nil
	default:
		return 0, fmt.Errorf("cannot convert %T to float64", v)
	}
}

// GetInt64 尝试将数据转换为int64
func (a *GenericAction) GetInt64() (int64, error) {
	switch v := a.data.(type) {
	case int64:
		return v, nil
	case int:
		return int64(v), nil
	case int32:
		return int64(v), nil
	case float64:
		return int64(v), nil
	case float32:
		return int64(v), nil
	default:
		return 0, fmt.Errorf("cannot convert %T to int64", v)
	}
}

// GetBool 尝试将数据转换为bool
func (a *GenericAction) GetBool() (bool, error) {
	switch v := a.data.(type) {
	case bool:
		return v, nil
	case int:
		return v != 0, nil
	case float64:
		return v != 0, nil
	default:
		return false, fmt.Errorf("cannot convert %T to bool", v)
	}
}

// GetString 尝试将数据转换为string
func (a *GenericAction) GetString() (string, error) {
	switch v := a.data.(type) {
	case string:
		return v, nil
	default:
		return fmt.Sprintf("%v", v), nil
	}
}

// GetSlice 尝试将数据转换为slice
func (a *GenericAction) GetSlice() ([]interface{}, error) {
	rv := reflect.ValueOf(a.data)
	if rv.Kind() != reflect.Slice && rv.Kind() != reflect.Array {
		return nil, fmt.Errorf("data is not a slice or array, got %T", a.data)
	}

	result := make([]interface{}, rv.Len())
	for i := 0; i < rv.Len(); i++ {
		result[i] = rv.Index(i).Interface()
	}
	return result, nil
}

// GetFloat64Slice 尝试将数据转换为[]float64
func (a *GenericAction) GetFloat64Slice() ([]float64, error) {
	slice, err := a.GetSlice()
	if err != nil {
		return nil, err
	}

	result := make([]float64, len(slice))
	for i, v := range slice {
		switch val := v.(type) {
		case float64:
			result[i] = val
		case float32:
			result[i] = float64(val)
		case int:
			result[i] = float64(val)
		case int64:
			result[i] = float64(val)
		case int32:
			result[i] = float64(val)
		default:
			return nil, fmt.Errorf("cannot convert element %d (%T) to float64", i, val)
		}
	}
	return result, nil
}
