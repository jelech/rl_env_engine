package core

import "fmt"

// ErrorCode 定义错误代码
type ErrorCode error

var (
	Success             ErrorCode = nil
	ErrNullPointer      ErrorCode = fmt.Errorf("null pointer error")
	ErrIndexOutOfBounds ErrorCode = fmt.Errorf("index out of bounds")
	ErrInvalidParameter ErrorCode = fmt.Errorf("invalid parameter")
	ErrUnexpected       ErrorCode = fmt.Errorf("unexpected error")
	ErrConfigInvalid    ErrorCode = fmt.Errorf("config validation failed")
	ErrScenarioNotFound ErrorCode = fmt.Errorf("scenario not found")
	ErrDataLoadFailed   ErrorCode = fmt.Errorf("data load failed")
	ErrStrategyFailed   ErrorCode = fmt.Errorf("strategy execution failed")
)

// SimulationError 仿真专用错误类型
type SimulationError struct {
	Code    ErrorCode
	Message string
	Cause   error
}

func (e *SimulationError) Error() string {
	if e.Cause != nil {
		return fmt.Sprintf("%s: %s (caused by: %v)", e.Code.Error(), e.Message, e.Cause)
	}
	return fmt.Sprintf("%s: %s", e.Code.Error(), e.Message)
}

func NewSimulationError(code ErrorCode, message string, cause error) *SimulationError {
	return &SimulationError{
		Code:    code,
		Message: message,
		Cause:   cause,
	}
}
