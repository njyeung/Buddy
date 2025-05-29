UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Windows_NT)
	BINARY_NAME := Buddy.exe
else
	BINARY_NAME := Buddy
endif

all: clean configure 
	cmake --build build
	@echo "Copying $(BINARY_NAME) to project root..."
	@cp build/bin/$(BINARY_NAME) ./$(BINARY_NAME)

configure:
	cmake -G Ninja -B build -S . -D CMAKE_BUILD_TYPE=Release

build:
	cmake --build build

copy:
	@echo "Copying $(BINARY_NAME) to project root..."
	@cp build/bin/$(BINARY_NAME) ./$(BINARY_NAME)

clean:
	@if [ -d build ]; then \
		echo "Removing build directory..."; \
		rm -rf build; \
	fi