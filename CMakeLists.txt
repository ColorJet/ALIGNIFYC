cmake_minimum_required(VERSION 3.20)

# Options - set these before project()
option(USE_CUDA "Enable CUDA acceleration" OFF)
option(BUILD_TESTS "Build test suite" OFF)
option(BUILD_GUI "Build Qt GUI application" OFF)
option(BUILD_PYTHON_BINDINGS "Build Python bindings" OFF)

# Determine languages
if(USE_CUDA)
    project(Alinify VERSION 1.0.0 LANGUAGES CXX CUDA)
else()
    project(Alinify VERSION 1.0.0 LANGUAGES CXX)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(USE_CUDA)
    set(CMAKE_CUDA_STANDARD 17)
    set(CMAKE_CUDA_STANDARD_REQUIRED ON)
endif()

# Export compile commands for IDEs
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Find packages (make most of them optional for basic build)
find_package(Threads REQUIRED)

# Optional packages
find_package(ITK QUIET)
find_package(Torch QUIET)
find_package(OpenCV QUIET)

if(USE_CUDA)
    find_package(CUDAToolkit QUIET)
    if(NOT CUDAToolkit_FOUND)
        message(WARNING "CUDA Toolkit not found. Disabling CUDA support.")
        set(USE_CUDA OFF)
    endif()
endif()

if(BUILD_PYTHON_BINDINGS)
    find_package(Python3 COMPONENTS Interpreter Development QUIET)
    find_package(pybind11 QUIET)
    if(NOT Python3_FOUND OR NOT pybind11_FOUND)
        message(WARNING "Python or pybind11 not found. Disabling Python bindings.")
        set(BUILD_PYTHON_BINDINGS OFF)
    endif()
endif()

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/src
)

# Add Gidel paths if they exist
set(GIDEL_SDK_PATH "C:/Program Files/Common Files/Gidel/SDK")
if(EXISTS "${GIDEL_SDK_PATH}/include")
    include_directories("${GIDEL_SDK_PATH}/include")
    link_directories("${GIDEL_SDK_PATH}/lib/libx64")
    set(HAS_GIDEL_SDK TRUE)
    message(STATUS "Found Gidel SDK at ${GIDEL_SDK_PATH}")
else()
    message(WARNING "Gidel SDK not found at ${GIDEL_SDK_PATH}. Camera module will not build.")
    set(HAS_GIDEL_SDK FALSE)
endif()

# Add optional includes
if(ITK_FOUND)
    include_directories(${ITK_INCLUDE_DIRS})
endif()

if(OpenCV_FOUND)
    include_directories(${OpenCV_INCLUDE_DIRS})
endif()

if(Torch_FOUND)
    include_directories(${TORCH_INCLUDE_DIRS})
endif()

# Add subdirectories
add_subdirectory(src/core)

if(HAS_GIDEL_SDK)
    add_subdirectory(src/camera)
endif()

if(OpenCV_FOUND)
    add_subdirectory(src/stitching)
    add_subdirectory(src/preprocessing)
endif()

if(ITK_FOUND)
    add_subdirectory(src/registration)
endif()

if(Torch_FOUND AND USE_CUDA)
    add_subdirectory(src/gpu_warp)
endif()

add_subdirectory(src/printer)

if(BUILD_PYTHON_BINDINGS)
    add_subdirectory(src/python_bindings)
endif()

if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Installation rules
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config/ DESTINATION config)

# Print configuration summary
message(STATUS "")
message(STATUS "=== Alinify Configuration Summary ===")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "CUDA support: ${USE_CUDA}")
message(STATUS "Python bindings: ${BUILD_PYTHON_BINDINGS}")
message(STATUS "Gidel SDK: ${HAS_GIDEL_SDK}")
message(STATUS "ITK: ${ITK_FOUND}")
message(STATUS "OpenCV: ${OpenCV_FOUND}")
message(STATUS "LibTorch: ${Torch_FOUND}")
message(STATUS "======================================")
message(STATUS "")
