#!/usr/bin/env python3
"""주석↔코드 재도출 검사기 (debt-070).

주석이 인용한 **좌표·이름·수치**를 코드에서 다시 이끌어내 대조한다.
잡는 것은 기계적 불일치 세 종류뿐이다:

    A 앵커   주석 속 `파일:줄` 이 존재하는가 (파일 실재 + 줄 범위 안)
    P 경로   줄 번호 없이 인용된 저장소 경로가 실재하는가
    B 심볼   주석 속 `A::B` · 파라미터 접두 · 인용 경로가 저장소에 존재하는가  (comment-check: ignore)
    C 상수   상수를 선언하는 줄의 꼬리 주석이 적은 수치가 그 선언값과 맞는가

**이 검사기가 잡지 못하는 것**(정직 선언 — 도구 출력에도 같은 문구를 낸다):
서술·해석·부호 규약·동작 설명. 예) "양 휠 동일 steer"(실제는 rear 만 offset),
"종료는 fine timeout 으로만"(실제는 settle 게이트), "+ left"(실제는 우측 양수).
2WS 감사 실측으로 **알려진 결함의 76% 가 이 범주**이며 사람/에이전트 판정이 필요하다.

사용:
    python3 Tools/comment_check/check_comments.py <경로...> [--repo-root DIR] [--json]

종료 코드: 0 = 불일치 없음, 1 = 불일치 있음, 2 = 사용법 오류.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

CODE_EXT = {".cpp", ".hpp", ".h", ".cc", ".py", ".yaml", ".yml", ".action", ".msg", ".srv", ".xml"}
CMAKE_NAMES = {"CMakeLists.txt"}

# 주석 안에서 파일 좌표를 인용한 형태:  path/to/file.ext:12   또는  file.ext:12-34
ANCHOR_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_.\-/]+\.(?:cpp|hpp|h|cc|py|yaml|yml|md|txt|action|msg|srv|xml|sh))"
    r"\s*:\s*(?P<a>\d+)(?:\s*-\s*(?P<b>\d+))?"
)
# C++ 정규화 이름 (Ns::Name).  (comment-check: ignore)
# 앞의 `(?<![.\w])` 는 `dual_steer_engine.py::KinematicEngine` 같은 **상류 출처 표기**를 제외한다 —
# `파일.확장자::함수` 는 C++ 이름이 아니라 이식 원본 좌표이고, 이 저장소에 없는 것이 정상이다.
QUALIFIED_RE = re.compile(r"(?<![.\w])(?P<ns>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)::(?P<name>[A-Za-z_]\w*)\b")
# yaml 파라미터 접두 인용:  translate_reverse_*  ·  `mpc_*`
PREFIX_RE = re.compile(r"`?\b(?P<prefix>[a-z][a-z0-9]*(?:_[a-z0-9]+)+)_\*")
# 위 접두를 **파라미터**로 읽어야 하는 문맥 신호 (없으면 멤버변수 등으로 보고 건너뛴다)
PARAM_CONTEXT_RE = re.compile(r"yaml|param|파라미터|ros2 param|declare_parameter|키\b")
# 줄 번호 없이 인용된 경로
CITED_PATH_RE = re.compile(r"(?<![/\w])(?P<p>(?:[A-Za-z0-9_.\-]+/){1,}[A-Za-z0-9_.\-]+)")
CITED_EXT = {".cpp", ".hpp", ".h", ".cc", ".py", ".yaml", ".yml", ".md", ".txt", ".action",
             ".msg", ".srv", ".xml", ".sh", ".drawio", ".json"}
# 상수 선언 + 꼬리 주석
CXX_CONST_RE = re.compile(
    r"^\s*(?:static\s+)?(?:constexpr|const)\s+\w[\w:<>]*\s+(?P<name>\w+)\s*=\s*(?P<expr>[^;]+);\s*//(?P<cmt>.*)$"
)
CXX_MEMBER_INIT_RE = re.compile(r"^\s*[\w:<>*&\s]+?(?P<name>\w+)\s*\{\s*(?P<expr>[^}]+)\}\s*;\s*//(?P<cmt>.*)$")
YAML_KV_RE = re.compile(r"^\s*(?P<key>[A-Za-z_][\w]*)\s*:\s*(?P<val>-?\d+(?:\.\d+)?)\s*#(?P<cmt>.*)$")
# 주석 속 수치 + 단위
NUM_UNIT_RE = re.compile(r"(?P<sign>[±+-]?)\s*(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>°|deg|dps|rad|mm|m/s|Hz|ms|s\b|m\b|%)")

# 이력 서술 신호 — 「무엇이 바뀌었나」이지 「코드가 무엇을 하나」가 아니다.
# 설계 근거(why)·제약·안전 경고는 잡지 않도록 **개정 서술 어휘만** 넣는다.
HISTORY_RE = re.compile(
    r"종전|정정했|정정해|해소했|교체됐|되돌렸|이 저장소에 없다|저장소에는 없다"
    r"|not present in this repository|In-repo trace"
    r"|\(\s*20\d\d-\d\d-\d\d\s*확인\s*\)"
)

# 억제 마커 — 이 토큰이 든 주석은 검사하지 않는다.
# 정당한 예외가 실재한다: (1) 결함 **예시**를 인용하는 문서·도구 (2) 붙여넣은 외부 로그
# (3) 상류 원본 좌표. 마커는 명시적이라 흔적이 남는다.
SUPPRESS = "comment-check: ignore"

DOC_DIRS = ("/docs/", "/doc/")


@dataclass
class Finding:
    check: str          # anchor | symbol | const
    file: str
    line: int
    comment: str
    detail: str

    def render(self) -> str:
        return f"{self.file}:{self.line}  [{self.check}] {self.detail}\n      | {self.comment.strip()[:150]}"


# ── 주석 추출 ────────────────────────────────────────────────────────────────
def _strip_cxx_strings(line: str) -> str:
    """문자열 리터럴 내용을 공백으로 덮어 // 오탐(URL·include 경로)을 줄인다.

    **길이를 보존한다** — 반환값의 인덱스를 원본 줄에 그대로 쓰기 때문이다.
    """
    out = list(line)
    i, n, in_str = 0, len(line), False
    while i < n:
        ch = line[i]
        if in_str:
            if ch == "\\" and i + 1 < n:
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == '"':
                in_str = False
            else:
                out[i] = " "
        elif ch == '"':
            in_str = True
        i += 1
    return "".join(out)


def _strip_py_strings(line: str) -> str:
    """Python 한 줄의 문자열 리터럴 내용을 공백으로 덮는다. **길이를 보존한다.**"""
    out = list(line)
    i, n, quote = 0, len(line), None
    while i < n:
        ch = line[i]
        if quote:
            if ch == "\\" and i + 1 < n:
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == quote:
                quote = None
            else:
                out[i] = " "
        elif ch in ("'", '"'):
            quote = ch
        i += 1
    return "".join(out)


def extract_comments(path: str, text: str):
    """(line_no, comment_text, full_line) 목록."""
    ext = os.path.splitext(path)[1]
    base = os.path.basename(path)
    lines = text.splitlines()
    res = []

    if ext in (".cpp", ".hpp", ".h", ".cc"):
        in_block = False
        for i, raw in enumerate(lines, 1):
            if in_block:
                end = raw.find("*/")
                res.append((i, raw[: end if end >= 0 else len(raw)], raw))
                if end >= 0:
                    in_block = False
                continue
            scan = _strip_cxx_strings(raw)
            pos = 0
            while pos < len(scan):
                b = scan.find("/*", pos)
                ln = scan.find("//", pos)
                if b >= 0 and (ln < 0 or b < ln):
                    end = scan.find("*/", b + 2)
                    res.append((i, raw[b + 2 : end if end >= 0 else len(raw)], raw))
                    if end < 0:
                        in_block = True
                        break
                    pos = end + 2          # 같은 줄의 다음 주석도 본다
                elif ln >= 0:
                    res.append((i, raw[ln + 2 :], raw))
                    break                  # // 뒤는 줄 끝까지 전부 주석
                else:
                    break
    elif ext == ".py":
        in_doc = None
        for i, raw in enumerate(lines, 1):
            if in_doc:
                res.append((i, raw, raw))
                if in_doc in raw:
                    in_doc = None
                continue
            st = raw.strip()
            if st.startswith('"""') or st.startswith("'''"):
                q = st[:3]
                res.append((i, raw, raw))
                if not (len(st) > 3 and st.endswith(q)):
                    in_doc = q
                continue
            # 문자열 안의 '#' 를 주석 시작으로 오인하지 않도록 리터럴을 먼저 덮는다.
            h = _strip_py_strings(raw).find("#")
            if h >= 0:
                res.append((i, raw[h + 1 :], raw))
    elif ext == ".xml":
        in_block = False
        in_desc = False
        for i, raw in enumerate(lines, 1):
            if in_desc:
                res.append((i, raw, raw))
                if "</description>" in raw:
                    in_desc = False
                continue
            if in_block:
                end = raw.find("-->")
                res.append((i, raw[: end if end >= 0 else len(raw)], raw))
                if end >= 0:
                    in_block = False
                continue
            b = raw.find("<!--")
            if b >= 0:
                end = raw.find("-->", b + 4)
                res.append((i, raw[b + 4 : end if end >= 0 else len(raw)], raw))
                in_block = end < 0
            if "<description>" in raw:
                res.append((i, raw, raw))  # description 은 산문이라 주석과 같이 본다
                in_desc = "</description>" not in raw
    elif ext in (".yaml", ".yml", ".action", ".msg", ".srv") or base in CMAKE_NAMES:
        for i, raw in enumerate(lines, 1):
            h = raw.find("#")
            if h >= 0:
                res.append((i, raw[h + 1 :], raw))
    return res


# ── 저장소 인덱스 ────────────────────────────────────────────────────────────
class RepoIndex:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.by_relpath: set[str] = set()
        self.by_basename: dict[str, list[str]] = {}
        self.dirs: set[str] = set()
        self._decl_cache: dict[str, bool] = {}
        self._param_cache: dict[str, bool] = {}
        self._corpus: str | None = None
        self._code_by_file: dict[str, str] | None = None
        self._scope_files: dict[str, list[str]] | None = None
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "build", "install", "log", "node_modules")]
            rel_dir = os.path.relpath(dirpath, self.root)
            self.dirs.add("." if rel_dir == "." else rel_dir)
            for fn in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fn), self.root)
                self.by_relpath.add(rel)
                self.by_basename.setdefault(fn, []).append(rel)

    @property
    def top_dirs(self) -> set[str]:
        if not hasattr(self, "_top"):
            self._top = {d.split("/", 1)[0] for d in self.dirs if d != "."}
        return self._top

    def exists_path(self, p: str) -> bool:
        """파일이든 디렉터리든, 정확히 또는 **경로 접미**로 일치하면 존재로 본다.

        디렉터리 성분이 있는 인용은 **파일명만 같은 것으로 통과시키지 않는다** —
        그렇게 하면 `docs/WRONG/params.yaml` 처럼 위치가 완전히 틀린 인용이 조용히 통과한다.  (comment-check: ignore)
        """
        if p in self.by_relpath or p in self.dirs:
            return True
        if any(x.endswith("/" + p) for x in self.by_relpath):
            return True
        if any(d == p or d.endswith("/" + p) for d in self.dirs):
            return True
        if "/" in p:
            return False
        return os.path.basename(p) in self.by_basename

    def resolve(self, cited: str) -> list[str]:
        """인용 경로를 저장소 상대경로 후보로 해석."""
        cited = cited.lstrip("./")
        if cited in self.by_relpath:
            return [cited]
        hits = [p for p in self.by_relpath if p.endswith("/" + cited)]
        if hits:
            return hits
        return list(self.by_basename.get(os.path.basename(cited), []))

    def line_count(self, rel: str) -> int:
        try:
            with open(os.path.join(self.root, rel), "rb") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0

    @property
    def corpus(self) -> str:
        """심볼 실재 판정용 **코드 본문**. 주석은 뺀다.

        주석을 남기면 주석에서만 언급되는 심볼이 스스로를 근거로 「선언됨」이 되어
        검사가 빈 통과한다(자기 인용). 이 검사기가 막으려는 부채와 같은 형태다.
        """
        if self._corpus is None:
            self._corpus = "\n".join(self.code_by_file.values())
        return self._corpus

    @property
    def code_by_file(self) -> dict[str, str]:
        """파일별 **주석 제거 본문**."""
        if self._code_by_file is None:
            out: dict[str, str] = {}
            for rel in self.by_relpath:
                if os.path.splitext(rel)[1] not in CODE_EXT and os.path.basename(rel) not in CMAKE_NAMES:
                    continue
                full = os.path.join(self.root, rel)
                try:
                    with open(full, encoding="utf-8", errors="ignore") as fh:
                        text = fh.read()
                except OSError:
                    continue
                cmt = {ln for ln, _, _ in extract_comments(full, text)}
                out[rel] = "\n".join(l for i, l in enumerate(text.splitlines(), 1) if i not in cmt)
            self._code_by_file = out
        return self._code_by_file

    def scope_files(self, scope: str) -> list[str]:
        """`namespace X` · `class X` · `struct X` 를 선언하는 파일들."""
        if self._scope_files is None:
            self._scope_files = {}
        if scope not in self._scope_files:
            pat = re.compile(r"\b(?:namespace|class|struct)\s+(?:\w+\s+)*" + re.escape(scope) + r"\b")
            self._scope_files[scope] = [rel for rel, body in self.code_by_file.items() if pat.search(body)]
        return self._scope_files[scope]

    def qualified_exists(self, full_name: str) -> bool:
        """`A::B::name` 이 **그 스코프 안에** 있는가.  (comment-check: ignore)

        마지막 이름만 저장소 어딘가에서 찾으면 `trnav_2ws_core::loadGeometry` 처럼  (comment-check: ignore)
        **이름은 맞고 소속이 틀린** 인용이 통과한다(실측 7건이 그 형태였다).  (comment-check: ignore)
        """
        if full_name in self.corpus:
            return True
        parts = full_name.split("::")
        name, scope = parts[-1], parts[-2] if len(parts) >= 2 else None
        if scope is None:
            return self.has_declaration(name)
        files = self.scope_files(scope)
        if not files:
            return False  # 스코프 자체가 없다
        pat = re.compile(r"\b" + re.escape(name) + r"\b")
        return any(pat.search(self.code_by_file[f]) for f in files)

    def has_declaration(self, name: str) -> bool:
        if name not in self._decl_cache:
            pat = re.compile(r"\b" + re.escape(name) + r"\b")
            self._decl_cache[name] = bool(pat.search(self.corpus))
        return self._decl_cache[name]

    def has_param_prefix(self, prefix: str) -> bool:
        if prefix not in self._param_cache:
            pat = re.compile(r"[\"'`]" + re.escape(prefix) + r"_[a-z0-9_]+[\"'`]|^\s*" + re.escape(prefix) + r"_[a-z0-9_]+\s*:", re.M)
            self._param_cache[prefix] = bool(pat.search(self.corpus))
        return self._param_cache[prefix]


# ── 검사 ─────────────────────────────────────────────────────────────────────
def check_anchor(idx: RepoIndex, rel: str, line: int, cmt: str, out: list[Finding]):
    for m in ANCHOR_RE.finditer(cmt):
        cited, a = m.group("path"), int(m.group("a"))
        b = int(m.group("b")) if m.group("b") else a
        if a < 1 or b < a:
            out.append(Finding("anchor", rel, line, cmt, f"줄 범위가 뒤집혔거나 0 이하다: {cited}:{a}-{b}"))
            continue
        cands = idx.resolve(cited)
        if not cands:
            out.append(Finding("anchor", rel, line, cmt, f"인용 파일이 저장소에 없다: {cited}"))
            continue
        if all(idx.line_count(c) < b for c in cands):
            best = max(idx.line_count(c) for c in cands)
            out.append(Finding("anchor", rel, line, cmt,
                               f"줄 범위 초과: {cited}:{a}{'-'+str(b) if b != a else ''} (해당 파일 {best}줄)"))


def check_history(rel: str, line: int, cmt: str, out: list[Finding]):
    """주석이 **코드가 하는 일**이 아니라 **무엇이 바뀌었는지**를 적고 있는가.

    이력은 패키지별 `docs/*_code_updates.md` 소관이다. 주석에 섞이면 주석이 두 시제를 갖고
    뒤엣것이 반드시 낡는다. 설계 근거(why)·제약·안전 경고는 이력이 아니므로 잡지 않는다.
    """
    m = HISTORY_RE.search(cmt)
    if m:
        out.append(Finding("history", rel, line, cmt,
                           f"이력 서술 — code_updates 소관이다: {m.group(0)!r}"))


def check_path(idx: RepoIndex, rel: str, line: int, cmt: str, out: list[Finding]):
    """줄 번호 없이 인용된 저장소 경로가 실재하는가.

    토픽(`/seer/robot_pose`)·메시지 타입(`nav_msgs/Path`)·단위(`deg/s`)·산문 슬래시(`QD/DD`)를
    걸러내려고, **저장소 최상위 디렉터리로 시작하거나 알려진 확장자로 끝나는 것만** 본다.
    """
    for m in CITED_PATH_RE.finditer(cmt):
        p = m.group("p").strip("`.,);:").rstrip("/").lstrip("./")
        if "/" not in p:
            continue
        top = p.split("/", 1)[0]
        ext = os.path.splitext(p)[1]
        if top not in idx.top_dirs and ext not in CITED_EXT:
            continue
        if idx.exists_path(p):
            continue
        out.append(Finding("path", rel, line, cmt, f"인용 경로가 저장소에 없다: {p}"))


def check_symbol(idx: RepoIndex, rel: str, line: int, cmt: str, out: list[Finding]):
    for m in QUALIFIED_RE.finditer(cmt):
        name = m.group("name")
        if len(name) < 4 or name.isupper():
            continue
        full_name = m.group(0)
        if not idx.qualified_exists(full_name):
            hint = "" if idx.has_declaration(name) else " (이름 자체가 없다)"
            if not hint:
                hint = f" (`{name}` 은 있으나 `{full_name.rsplit('::', 1)[0]}` 소속이 아니다)"
            out.append(Finding("symbol", rel, line, cmt, f"인용 심볼을 그 스코프에서 찾을 수 없다: {full_name}{hint}"))
    # 파라미터 접두는 **파라미터 문맥**에서만 본다 — 멤버변수 접두를 걸러낸다.  (comment-check: ignore)
    if PARAM_CONTEXT_RE.search(cmt):
        for m in PREFIX_RE.finditer(cmt):
            p = m.group("prefix")
            if not idx.has_param_prefix(p):
                out.append(Finding("symbol", rel, line, cmt, f"인용 파라미터 접두로 시작하는 키가 없다: {p}_*"))


# 주석이 값 대신 **범위·증분·비교**를 말하는 형태 — 선언값과 같을 이유가 없다.
RANGE_HINT_RE = re.compile(
    r"사이|이상|이하|초과|미만|범위|~\s*\d|\bbetween\b|\brange\b"
    r"|(?:최대|최소|\bmax\b|\bmin\b)\s*[±+-]?\s*\d"          # 「최대 6°」처럼 숫자에 붙을 때만
    r"|(?<=[\w)])\s*[+\-*/]\s*\d+(?:\.\d+)?\s*(?:°|deg|m\b|s\b|mm)"  # 증분식 (lookahead+0.2 m)"
)

# 코드 선언값을 주석 단위로 환산하는 배수 (선언 단위 → 주석 단위)
UNIT_SCALE = {
    "mm": 1000.0, "m": 1.0, "m/s": 1.0, "%": 100.0,
    "ms": 1000.0, "s": 1.0, "Hz": 1.0, "dps": 1.0, "rad": 1.0,
}
DEG_UNITS = ("°", "deg")


def _tolerance_for(token: str, value: float) -> float:
    """주석이 쓴 유효숫자만큼만 요구한다. `89.94` 는 ±0.005, `115` 는 ±0.5."""
    frac = len(token.split(".")[1]) if "." in token else 0
    return 0.5 * (10.0 ** -frac) + abs(value) * 1e-9


def _eval_expr(expr: str) -> float | None:
    e = expr.strip()
    e = re.sub(r"\b(0[xX][0-9a-fA-F]+)\b", lambda m: str(int(m.group(1), 16)), e)   # 16진수
    e = re.sub(r"(?<=[0-9.])[uUlLfF]+\b", "", e)                                     # u/l/f 접미사
    e = e.replace("M_PI", "3.141592653589793")
    if not re.fullmatch(r"[0-9eE+\-*/.() ]+", e):
        return None
    try:
        return float(eval(e, {"__builtins__": {}}, {}))  # noqa: S307 - 숫자 리터럴만 통과
    except Exception:
        return None


def check_const(rel: str, line: int, full: str, out: list[Finding]):
    for rx in (CXX_CONST_RE, CXX_MEMBER_INIT_RE, YAML_KV_RE):
        m = rx.match(full)
        if not m:
            continue
        cmt = m.group("cmt")
        if RANGE_HINT_RE.search(cmt):
            return  # 범위·증분·비교 서술은 선언값과 같을 이유가 없다
        val = _eval_expr(m.group("val") if "val" in m.groupdict() else m.group("expr"))
        if val is None:
            return
        deg = val * 180.0 / 3.141592653589793
        nums = list(NUM_UNIT_RE.finditer(cmt))
        if not nums:
            return
        matched, unmatched = [], []
        for nm in nums:
            tok, unit, sign = nm.group("num"), nm.group("unit"), nm.group("sign")
            n = float(tok)
            if sign == "-":
                n = -n            # 부호를 버리면 `= 10.0; // -10 m` 가 통과한다
            # 라디안 선언 ↔ 도 표기, m 선언 ↔ mm 표기 등 단위 환산을 모두 시도한다.
            targets = [val * UNIT_SCALE.get(unit, 1.0)]
            if unit in DEG_UNITS:
                targets.append(deg)
            if abs(n - val) < abs(n - targets[0]):
                targets.append(val)  # 단위를 못 읽었을 때의 원값 비교
            if sign == "±":
                targets = [abs(t) for t in targets]
                n = abs(n)
            (matched if any(abs(n - t) <= _tolerance_for(tok, t) for t in targets)
             else unmatched).append(nm)
        # 하나라도 맞으면 통과한다. 「전부 맞아야 한다」로 조이면 **파생 수치**를 언급하는
        # 정상 주석이 오탐된다 — 실측 3건: `10 Hz 기준 약 1.0 s`(선언은 샘플 수 10),
        # `이산화 지연 50ms→20ms`(선언은 50 Hz). 그 대가로 「10 m 이고 또한 999 m」 처럼
        # 같은 주석 안의 거짓 주장 하나는 놓친다(README «알려진 미해결»).
        if matched or not unmatched:
            return
        nums = unmatched
        shown = ", ".join(f'{x.group("sign")}{x.group("num")}{x.group("unit")}' for x in nums)
        out.append(Finding("const", rel, line, cmt,
                           f"선언값과 어긋난다: 코드 {val:g}"
                           f"{f' (= {deg:g}°)' if abs(deg - val) > 1e-9 else ''} vs 주석 {shown}"))
        return


def scan_file(idx: RepoIndex, path: str, checks: set[str]) -> list[Finding]:
    rel = os.path.relpath(os.path.abspath(path), idx.root)
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return []
    out: list[Finding] = []
    for line, cmt, full in extract_comments(path, text):
        if SUPPRESS in cmt:
            continue
        if "anchor" in checks:
            check_anchor(idx, rel, line, cmt, out)
        if "path" in checks:
            check_path(idx, rel, line, cmt, out)
        if "history" in checks:
            check_history(rel, line, cmt, out)
        if "symbol" in checks:
            check_symbol(idx, rel, line, cmt, out)
        if "const" in checks:
            check_const(rel, line, full, out)
    return out


def iter_targets(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        else:
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in (".git", "build", "install", "log")]
                if any(d in dirpath for d in DOC_DIRS):
                    continue
                for fn in filenames:
                    if os.path.splitext(fn)[1] in CODE_EXT or fn in CMAKE_NAMES:
                        yield os.path.join(dirpath, fn)


LIMITS = (
    "검사 범위: 인용 좌표·이름·선언 수치만 검증됨(history 는 --checks 로 옵트인). "
    "서술·부호 규약·동작 설명은 미검증 — 사람/에이전트 판정 필요."
)


def main() -> int:
    ap = argparse.ArgumentParser(description="주석↔코드 재도출 검사기 (debt-070)")
    ap.add_argument("paths", nargs="+", help="검사할 파일 또는 디렉터리")
    ap.add_argument("--repo-root", default=None, help="저장소 루트 (기본: git rev-parse)")
    ap.add_argument("--checks", default="anchor,path,symbol,const", help="anchor,path,symbol,const,history 중 쉼표 구분 (history 는 기본 미포함 — 옵트인)")
    ap.add_argument("--json", action="store_true", help="JSON 으로 출력")
    a = ap.parse_args()

    root = a.repo_root
    if not root:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        root = r.stdout.strip() if r.returncode == 0 else os.getcwd()

    valid = {"anchor", "path", "symbol", "const", "history"}
    checks = {c.strip() for c in a.checks.split(",") if c.strip()}
    if not checks or (checks - valid):
        ap.error(f"--checks 에 알 수 없는 값: {sorted(checks - valid) or '(빈 값)'} — 가능: {sorted(valid)}")
    missing = [p for p in a.paths if not os.path.exists(p)]
    if missing:
        ap.error(f"대상 경로가 없다: {missing}")
    idx = RepoIndex(root)

    findings, n_files = [], 0
    for f in iter_targets(a.paths):
        n_files += 1
        findings.extend(scan_file(idx, f, checks))

    if a.json:
        print(json.dumps({"limits": LIMITS, "files": n_files,
                          "findings": [asdict(x) for x in findings]}, ensure_ascii=False, indent=1))
    else:
        for x in findings:
            print(x.render())
        print(f"\n파일 {n_files}개 · 불일치 {len(findings)}건")
        print(f"⚠ {LIMITS}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
