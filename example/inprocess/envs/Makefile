CC      = gcc
CFLAGS  = -O2 -fPIC -Wall

UNAME := $(shell uname)
ifeq ($(UNAME), Darwin)
	SHARED_FLAG = -dynamiclib
	LIB_NAME    = libtracker.dylib
else
	SHARED_FLAG = -shared
	LIB_NAME    = libtracker.so
endif

.PHONY: all clean cython

all: $(LIB_NAME) cython

$(LIB_NAME): tracker_c.c env_interface.h
	$(CC) $(CFLAGS) $(SHARED_FLAG) -o $@ tracker_c.c -lm

cython:
	python setup.py build_ext --inplace

clean:
	rm -f $(LIB_NAME) tracker_cython*.so tracker_cython*.dylib tracker_cython.c
	rm -rf build/
