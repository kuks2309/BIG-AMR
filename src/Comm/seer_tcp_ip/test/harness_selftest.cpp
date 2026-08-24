// 하니스 자기시험 — 각 매크로가 「실패해야 할 입력」에서 실제로 실패를 검출하는가.
//
// 이것이 통과하지 않으면 나머지 시험의 통과 숫자는 의미가 없다. 초판 CHECK_THROWS_MSG 는
// **예외가 아예 안 나면 실패로 잡지 않는 구멍**이 있었고, 이 시험이 그것을 드러냈다.
// 빌드타입이 Release(-DNDEBUG) 여도 매크로가 살아 있어야 한다 — assert 를 쓰지 않는 이유다.
#include <stdexcept>

#include "harness.hpp"

namespace
{
bool detected(int before)
{
    return harness::g_fail == before + 1;
}
}  // namespace

int main()
{
    CASE("selftest");
    int before;
    int problems = 0;

    before = harness::g_fail;
    CHECK(false);
    if (!detected(before)) { std::fprintf(stderr, "X CHECK 미검출\n"); ++problems; }

    before = harness::g_fail;
    CHECK_EQ(1, 2);
    if (!detected(before)) { std::fprintf(stderr, "X CHECK_EQ 미검출\n"); ++problems; }

    // 예외가 아예 안 나는 경우 — 초판에서 놓쳤던 구멍
    before = harness::g_fail;
    CHECK_THROWS_MSG((void)0, std::runtime_error, "아무거나");
    if (!detected(before)) { std::fprintf(stderr, "X CHECK_THROWS_MSG(무예외) 미검출\n"); ++problems; }

    // 예외는 나지만 메시지가 다른 경우
    before = harness::g_fail;
    CHECK_THROWS_MSG(throw std::runtime_error("다른말"), std::runtime_error, "찾는말");
    if (!detected(before)) { std::fprintf(stderr, "X CHECK_THROWS_MSG(메시지불일치) 미검출\n"); ++problems; }

    // 예외 종류가 다른 경우
    before = harness::g_fail;
    CHECK_THROWS_MSG(throw std::logic_error("x"), std::overflow_error, "x");
    if (!detected(before)) { std::fprintf(stderr, "X CHECK_THROWS_MSG(종류불일치) 미검출\n"); ++problems; }

    before = harness::g_fail;
    CHECK_NOTHROW(throw std::runtime_error("boom"));
    if (!detected(before)) { std::fprintf(stderr, "X CHECK_NOTHROW 미검출\n"); ++problems; }

    if (problems != 0)
    {
        std::fprintf(stderr, "하니스 자기시험 실패 %d건 — 다른 시험의 통과는 믿을 수 없다\n", problems);
        return 1;
    }
    std::fprintf(stderr, "harness_selftest: 6개 매크로 전부 실패를 검출한다 (의도된 FAIL 로그 6줄 위)\n");
    return 0;
}
