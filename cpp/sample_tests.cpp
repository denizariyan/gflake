#include <gtest/gtest.h>
#include <chrono>
#include <thread>
#include <random>

class BasicTests : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

TEST_F(BasicTests, FastTest) {
    EXPECT_EQ(1 + 1, 2);
}

TEST_F(BasicTests, SlowTest) {
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    EXPECT_TRUE(true);
}

TEST_F(BasicTests, VerySlowTest) {
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    EXPECT_TRUE(true);
}

TEST_F(BasicTests, LongRunningTest) {
    std::this_thread::sleep_for(std::chrono::seconds(2));
    EXPECT_TRUE(true);
}

// A flaky test that fails ~10% of the time
TEST_F(BasicTests, FlakyTest) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 10);
    
    int random_value = dis(gen);
    
    if (random_value == 1) {
        FAIL() << "Simulated flaky test failure (random value: " << random_value << ")";
    }
    
    EXPECT_TRUE(true);
}

class MathTests : public ::testing::Test {};

TEST_F(MathTests, Addition) {
    EXPECT_EQ(5 + 3, 8);
}

TEST_F(MathTests, Multiplication) {
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    EXPECT_EQ(4 * 3, 12);
}

TEST_F(MathTests, Division) {
    EXPECT_EQ(10 / 2, 5);
}

class ParameterizedTest : public ::testing::TestWithParam<int> {};

TEST_P(ParameterizedTest, IsEven) {
    int value = GetParam();
    EXPECT_EQ(value % 2, 0);
}

INSTANTIATE_TEST_SUITE_P(EvenNumbers, ParameterizedTest, 
                         ::testing::Values(2, 4, 6, 8, 10));

template <typename T>
class TypedTest : public ::testing::Test {};

using MyTypes = ::testing::Types<int, float, double>;
TYPED_TEST_SUITE(TypedTest, MyTypes);

TYPED_TEST(TypedTest, DefaultConstruction) {
    TypeParam value{};
    EXPECT_EQ(value, TypeParam{});
}

TYPED_TEST(TypedTest, Assignment) {
    TypeParam value{};
    value = static_cast<TypeParam>(42);
    EXPECT_EQ(value, static_cast<TypeParam>(42));
}

// Not part of a fixture
TEST(SimpleTests, TrueIsTrue) {
    EXPECT_TRUE(true);
}

TEST(SimpleTests, FalseIsFalse) {
    std::this_thread::sleep_for(std::chrono::milliseconds(25));
    EXPECT_FALSE(false);
}