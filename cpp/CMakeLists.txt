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

option(VISION_INSPECTOR_BUILD_TESTS
       "Build GoogleTest-based unit tests for the inspection engine"
       OFF)

# Allow user to point CMake at a custom OpenCV install (e.g. Homebrew on Apple
# Silicon installs to /opt/homebrew, Intel Macs to /usr/local).
find_package(OpenCV REQUIRED COMPONENTS core imgproc imgcodecs)

# Engine sources WITHOUT main.cpp so the test binary can link the same code.
set(VISION_INSPECTOR_LIB_SOURCES
    src/Preprocessor.cpp
    src/DefectDetector.cpp
    src/Measurement.cpp
    src/InspectionEngine.cpp
    src/ReportWriter.cpp
)

add_library(vision_inspector_core STATIC ${VISION_INSPECTOR_LIB_SOURCES})
target_include_directories(vision_inspector_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${OpenCV_INCLUDE_DIRS}
)
target_link_libraries(vision_inspector_core PUBLIC ${OpenCV_LIBS})

add_executable(vision_inspector src/main.cpp)
target_link_libraries(vision_inspector PRIVATE vision_inspector_core)

set_target_properties(vision_inspector PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
)

message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")

# --- GoogleTest (optional) ---------------------------------------------------
if(VISION_INSPECTOR_BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG        v1.14.0
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    enable_testing()

    add_executable(vision_inspector_tests
        tests/test_measurement.cpp
        tests/test_verdict.cpp
        tests/test_report_writer.cpp
    )
    target_link_libraries(vision_inspector_tests
        PRIVATE vision_inspector_core GTest::gtest_main)

    include(GoogleTest)
    gtest_discover_tests(vision_inspector_tests)
endif()
