cmake_minimum_required(VERSION 3.10)
project(cfft)

set(CMAKE_CXX_STANDARD 17)

add_executable(cfft main.cpp FFT.cpp FFT.h Utils.cpp Utils.h)

# Locate GTest
# find_package(GTest REQUIRED)
# include_directories(${GTEST_INCLUDE_DIRS})

# googletest-release-1.8.1
################################
# GTest
################################
ADD_SUBDIRECTORY (googletest-release-1.8.1)
enable_testing()
include_directories(${gtest_SOURCE_DIR}/include ${gtest_SOURCE_DIR})

# Link runTests with what we want to test and the GTest and pthread library
add_executable(runTests FFTTest.cpp Utils.cpp Utils.h FFT.cpp FFT.h)
target_link_libraries(runTests ${GTEST_LIBRARIES} pthread)

