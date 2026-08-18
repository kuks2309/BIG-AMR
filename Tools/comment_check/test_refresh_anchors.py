#!/usr/bin/env python3
"""refresh_anchors 계약 시험.

이 도구가 틀리면 **표가 조용히 엉뚱한 코드를 가리킨다** — coding SOP §2 가 그 표를
선독하게 하므로 비용이 곧바로 발생한다. 그래서 놓치기 쉬운 네 가지를 고정한다:
생성자 · 이름공간 스코프 상수 · 다중 이름 행 · 호출부 오인.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "refresh_anchors.py")

SRC = """\
#include <cstdint>

namespace demo
{

inline constexpr int kLimit = 7;

class Widget
{
  public:
    // 생성자 — 반환형이 없어 이름이 줄 맨 앞에 온다.
    Widget() : count_(0)
    {
    }

    void bump()
    {
        helper();
    }

    void helper()
    {
        ++count_;
    }

  private:
    int count_ = 0;
    int spare_ = 0;
};

} // namespace demo
"""

# 클래스 밖 정의 — `void Widget::attach(...)` 의 `attach(` 앞은 `::` 로 끝난다.
#   초기화 리스트 배제 규칙이 이것까지 먹으면 클래스 밖 정의를 통째로 놓친다.
SRC_OUT = """\
#include "demo.hpp"

namespace demo
{

void Widget::attach(int n)
{
    count_ = n;
}

} // namespace demo
"""

TABLE = """\
# 표

| 함수 | 위치 | 비고 |
| --- | --- | --- |
| `Widget()` 생성자 | demo.hpp:1-1 | 생성자 |
| `bump()` | demo.hpp:1-1 | 함수 |
| `helper()` | demo.hpp:1-1 | 호출부와 헷갈리기 쉬움 |
| `kLimit` | demo.hpp:1-1 | 이름공간 스코프 상수 |
| `count_` / `spare_` | demo.hpp:1-1 | 다중 이름 |
| `Widget::attach(n)` | demo.cpp:1-1 | 클래스 밖 정의 |
"""

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print(f"[FAIL] {msg}")


with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "demo.hpp"), "w").write(SRC)
    open(os.path.join(d, "demo.cpp"), "w").write(SRC_OUT)
    table = os.path.join(d, "table.md")
    open(table, "w").write(TABLE)

    r = subprocess.run([sys.executable, TOOL, table, d], capture_output=True, text=True)
    check("미해결 0건" in r.stdout, f"미해결이 남았다:\n{r.stdout}")

    got = {}
    for line in open(table):
        for fname in ("demo.hpp:", "demo.cpp:"):
            if line.startswith("| `") and fname in line:
                cell = line.split("| " + fname)[0]
                got[cell.strip()] = line.split("| " + fname)[1].split(" |")[0]

    lines = SRC.split("\n")

    def line_of(text):
        return next(i + 1 for i, l in enumerate(lines) if text in l)

    ctor = line_of("Widget() : count_(0)")
    check(got.get("| `Widget()` 생성자") == f"{ctor - 1}-{ctor + 2}",
          f"생성자 앵커가 주석 포함 정의 범위가 아니다: {got.get('| `Widget()` 생성자')}")

    bump = line_of("void bump()")
    check(got.get("| `bump()`") == f"{bump}-{bump + 3}", f"함수 앵커가 틀렸다: {got.get('| `bump()`')}")

    helper = line_of("void helper()")
    check(got.get("| `helper()`") == f"{helper}-{helper + 3}",
          f"호출부를 정의로 오인했다: {got.get('| `helper()`')}")

    klimit = line_of("inline constexpr int kLimit")
    check(got.get("| `kLimit`") == f"{klimit}-{klimit}",
          f"이름공간 스코프 상수를 못 찾았다: {got.get('| `kLimit`')}")

    c = line_of("int count_ = 0;")
    s = line_of("int spare_ = 0;")
    check(got.get("| `count_` / `spare_`") == f"{c}-{s}",
          f"다중 이름 행이 전체를 덮지 않는다: {got.get('| `count_` / `spare_`')}")

    out_lines = SRC_OUT.split("\n")
    attach = next(i + 1 for i, l in enumerate(out_lines) if "void Widget::attach" in l)
    check(got.get("| `Widget::attach(n)`") == f"{attach}-{attach + 3}",
          f"클래스 밖 정의를 초기화 리스트로 오인했다: {got.get('| `Widget::attach(n)`')}")

    # 갱신 후 --check 는 조용해야 한다(멱등).
    r2 = subprocess.run([sys.executable, TOOL, "--check", table, d], capture_output=True, text=True)
    check(r2.returncode == 0 and "어긋남 0건" in r2.stdout, f"멱등하지 않다:\n{r2.stdout}")

if fails:
    print(f"\n[FAIL] {len(fails)} 건 실패")
    sys.exit(1)
print("[PASS] refresh_anchors 계약 시험 통과")
