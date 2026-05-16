cmake_minimum_required(VERSION 3.14)
project(vision_inspector LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

if(MSVC)
    add_compile_options(/W3)
else()
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Allow user to point CMake at a custom OpenCV install (e.g. Homebrew on Apple
# Silicon installs to /opt/homebrew, Intel Macs to /usr/local).
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs)

set(VISION_INSPECTOR_SOURCES
    src/main.cpp
    src/Preprocessor.cpp
    src/DefectDetector.cpp
    src/Measurement.cpp
    src/InspectionEngine.cpp
    src/ReportWriter.cpp
)

add_executable(vision_inspector ${VISION_INSPECTOR_SOURCES})

target_include_directories(vision_inspector
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${OpenCV_INCLUDE_DIRS}
)

target_link_libraries(vision_inspector PRIVATE ${OpenCV_LIBS})

# Place the resulting binary in <project-root>/build (one level above cpp/)
# when the user follows the documented `cmake -S cpp -B build` workflow,
# OpenCV CMake builds always place the binary in CMAKE_BINARY_DIR which is
# exactly `build/` in that case.
set_target_properties(vision_inspector PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)

message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")
