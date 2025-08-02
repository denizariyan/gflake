cmake_minimum_required(VERSION 3.14)
project(gflake_test_binary)

set(CMAKE_CXX_STANDARD 17)

# Find GTest
find_package(GTest REQUIRED)

# Create test binary with various test types
add_executable(test_binary
    sample_tests.cpp
)

# Create an empty test binary (no tests)
add_executable(empty_test_binary
    empty_tests.cpp
)


target_link_libraries(test_binary
    GTest::gtest
    GTest::gtest_main
)

target_link_libraries(empty_test_binary
    GTest::gtest
    GTest::gtest_main
)

# Enable testing

enable_testing()
add_test(NAME all_tests COMMAND test_binary)
add_test(NAME empty_tests COMMAND empty_test_binary)