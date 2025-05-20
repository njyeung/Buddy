all: clean configure 
	cmake --build build
	@echo "Copying Buddy.exe to project root..."
	@cp build/bin/Buddy.exe ./Buddy.exe

configure:
	cmake -G Ninja -B build -S . -D CMAKE_BUILD_TYPE=Release

build:
	cmake --build build

copy:
	@echo "Copying Buddy.exe to project root..."
	@cp build/bin/Buddy.exe ./Buddy.exe

clean:
	@if [ -d build ]; then \
		echo "Removing build directory..."; \
		rm -rf build; \
	fi