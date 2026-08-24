// 자체 시험 하니스 — gtest 를 쓰지 않는다(저장소에 1건뿐이고, mcl2d_core 관례가 자체 하니스다).
//
// assert 를 쓰지 않는 이유: 기본 빌드타입이 Release(-DNDEBUG)라 assert 가 사라져 시험이 무조건
// 통과한다. 아래 매크로는 NDEBUG 와 무관하게 실패한다.
#ifndef SEER_TCP_IP_TEST_HARNESS_HPP_
#define SEER_TCP_IP_TEST_HARNESS_HPP_

#include <cstdio>
#include <cstdlib>
#include <exception>
#include <string>

namespace harness
{
inline int g_pass = 0;
inline int g_fail = 0;
inline const char *g_case = "";

inline void fail(const char *file, int line, const std::string &what)
{
    ++g_fail;
    std::fprintf(stderr, "  FAIL [%s] %s:%d — %s\n", g_case, file, line, what.c_str());
}

inline int report(const char *suite)
{
    std::fprintf(stderr, "%s: %d passed, %d failed\n", suite, g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
}  // namespace harness

#define CASE(name) harness::g_case = (name)

#define CHECK(expr)                                                                 \
    do                                                                              \
    {                                                                               \
        if (!(expr))                                                                \
        {                                                                           \
            harness::fail(__FILE__, __LINE__, "CHECK(" #expr ")");                  \
        }                                                                           \
        else                                                                        \
        {                                                                           \
            ++harness::g_pass;                                                      \
        }                                                                           \
    } while (0)

#define CHECK_EQ(a, b)                                                              \
    do                                                                              \
    {                                                                               \
        auto _a = (a);                                                              \
        auto _b = (b);                                                              \
        if (!(_a == _b))                                                            \
        {                                                                           \
            harness::fail(__FILE__, __LINE__, "CHECK_EQ(" #a ", " #b ")");          \
        }                                                                           \
        else                                                                        \
        {                                                                           \
            ++harness::g_pass;                                                      \
        }                                                                           \
    } while (0)

/// 예외 종류와 메시지 조각을 함께 본다 — 종류만 보면 다른 가드가 대신 걸려도 통과한다
/// (Python 판에서 실제로 그 함정을 밟았다: duration 가드를 지워도 interval 가드가 같은
///  문자열을 담아 match 를 통과했다).
#define CHECK_THROWS_MSG(stmt, ExcType, needle)                                     \
    do                                                                              \
    {                                                                               \
        bool _ok = false;                                                           \
        bool _threw = false;                                                        \
        try                                                                         \
        {                                                                           \
            stmt;                                                                   \
        }                                                                           \
        catch (const ExcType &_e)                                                   \
        {                                                                           \
            _threw = true;                                                          \
            _ok = std::string(_e.what()).find(needle) != std::string::npos;          \
            if (!_ok)                                                               \
            {                                                                       \
                harness::fail(__FILE__, __LINE__,                                   \
                              std::string("메시지에 '") + needle + "' 없음: " + _e.what()); \
            }                                                                       \
        }                                                                           \
        catch (const std::exception &_e)                                            \
        {                                                                           \
            _threw = true;                                                          \
            harness::fail(__FILE__, __LINE__, std::string("다른 예외: ") + _e.what()); \
        }                                                                           \
        if (!_threw)                                                                \
        {                                                                           \
            harness::fail(__FILE__, __LINE__, "예외가 발생하지 않았다: " #stmt);        \
        }                                                                           \
        if (_ok)                                                                    \
        {                                                                           \
            ++harness::g_pass;                                                      \
        }                                                                           \
    } while (0)

#define CHECK_NOTHROW(stmt)                                                         \
    do                                                                              \
    {                                                                               \
        try                                                                         \
        {                                                                           \
            stmt;                                                                   \
            ++harness::g_pass;                                                      \
        }                                                                           \
        catch (const std::exception &_e)                                            \
        {                                                                           \
            harness::fail(__FILE__, __LINE__, std::string("예외 발생: ") + _e.what()); \
        }                                                                           \
    } while (0)

#endif  // SEER_TCP_IP_TEST_HARNESS_HPP_
