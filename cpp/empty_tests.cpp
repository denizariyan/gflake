#include <gtest/gtest.h>

// This binary intentionally contains no tests.

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
