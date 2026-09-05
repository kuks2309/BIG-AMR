// NDEBUG 무관 검증 매크로.
//
// `assert` 를 쓰지 않는다 — 기본 빌드타입이 Release(`-DNDEBUG`) 라 assert 는 빈 문장으로 사라지고,
// 그러면 어떤 결함이 있어도 시험이 `return 0` 한다. 이 저장소는 그 사고를 이미 겪었다
// (src/Navigation/README.md:74-76 — `test_mcl2d` 의 assert 3개가 전부 컴파일아웃돼 있었다).
// `mcl2d_map` 의 `test_smap` 이 같은 이유로 자체 매크로를 쓴다 — 그 방식을 따른다.
#ifndef SLAM_KARTO_CORE_TEST_CHECK_HPP
#define SLAM_KARTO_CORE_TEST_CHECK_HPP

#include <cstdio>
#include <cstdlib>

namespace slam_karto_core_test
{
inline int &failureCount()
{
    static int n = 0;
    return n;
}
} // namespace slam_karto_core_test

/// 조건이 거짓이면 즉시 실패를 기록하고 메시지를 출력한다(계속 진행 — 전체 결함을 한 번에 본다).
#define CHECK(cond, msg)                                                                           \
    do                                                                                             \
    {                                                                                              \
        if (!(cond))                                                                               \
        {                                                                                          \
            std::printf("[FAIL] %s:%d  %s  — %s\n", __FILE__, __LINE__, #cond, (msg));             \
            ++slam_karto_core_test::failureCount();                                                \
        }                                                                                          \
    } while (0)

/// 조건이 거짓이면 즉시 프로세스를 죽인다(이후 검사가 무의미해지는 전제 조건용).
#define CHECK_FATAL(cond, msg)                                                                     \
    do                                                                                             \
    {                                                                                              \
        if (!(cond))                                                                               \
        {                                                                                          \
            std::printf("[FATAL] %s:%d  %s  — %s\n", __FILE__, __LINE__, #cond, (msg));            \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (0)

/// main 말미에서 호출 — 실패가 하나라도 있으면 1, 없으면 0.
#define CHECK_SUMMARY()                                                                            \
    (slam_karto_core_test::failureCount() == 0                                                     \
         ? (std::printf("[PASS] 전 검사 통과\n"), 0)                                               \
         : (std::printf("[FAIL] 실패 %d건\n", slam_karto_core_test::failureCount()), 1))

#endif // SLAM_KARTO_CORE_TEST_CHECK_HPP
