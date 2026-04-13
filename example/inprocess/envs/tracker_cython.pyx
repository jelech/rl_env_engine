# cython: language_level=3, boundscheck=False, wraparound=False
"""
Cython 环境示例 - 1D Tracker

与 tracker_python.py 相同的逻辑，但:
- 状态用 cdef 属性存储，访问零开销
- cpdef 方法可从 Python 和 Cython 两侧调用
- 数值计算部分使用 C math 库

编译:
    cd envs && python setup.py build_ext --inplace
"""

import numpy as np
cimport numpy as cnp
from libc.math cimport fabs
from libc.stdlib cimport rand, RAND_MAX

cnp.import_array()


cdef class TrackerEnv:
    cdef double position
    cdef double target
    cdef int step_count
    cdef int max_steps
    cdef double dt
    cdef double noise_scale

    def __init__(self, dict config=None):
        if config is None:
            config = {}
        self.target = config.get("target", 1.0)
        self.max_steps = config.get("max_steps", 200)
        self.dt = config.get("dt", 0.1)
        self.noise_scale = config.get("noise", 0.01)
        self.position = 0.0
        self.step_count = 0

    cpdef tuple reset(self):
        self.position = 0.0
        self.step_count = 0
        cdef cnp.ndarray[cnp.float64_t, ndim=1] obs = np.array(
            [self.position, self.target], dtype=np.float64
        )
        return obs, {}

    cpdef tuple step(self, object action):
        cdef double act
        if isinstance(action, np.ndarray):
            act = action.flat[0]
        else:
            act = <double>action

        if act > 1.0:
            act = 1.0
        elif act < -1.0:
            act = -1.0

        # 用 C 标准库生成噪声，避免 Python 调用开销
        cdef double noise = ((<double>rand() / RAND_MAX) * 2.0 - 1.0) * self.noise_scale
        self.position = self.position + act * self.dt + noise
        self.step_count = self.step_count + 1

        cdef double reward = -fabs(self.position - self.target)
        cdef bint done = self.step_count >= self.max_steps

        cdef cnp.ndarray[cnp.float64_t, ndim=1] obs = np.array(
            [self.position, self.target], dtype=np.float64
        )
        return obs, reward, done, False, {}

    cpdef void close(self):
        pass
