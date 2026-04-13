"""
Cython 环境编译脚本

用法:
    python setup.py build_ext --inplace
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np

extensions = [
    Extension(
        "tracker_cython",
        ["tracker_cython.pyx"],
        include_dirs=[np.get_include()],
        extra_compile_args=["-O2"],
    ),
]

setup(
    name="tracker_cython_env",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
        },
    ),
)
