"""ROS 무의존 불변식 — ADR 2026-07-28 §Decision 2.

Phase 1 모듈이 `rclpy` 를 끌어오면 ROS 가 죽은 순간 감시기도 같이 죽는다. 이 요건은 문서
약속으로는 지켜지지 않으므로(다음 사람이 무심코 import 한다) 테스트로 못박는다.

두 방향으로 검사한다:
  ① 정적 — `import rclpy` / `from rclpy ...` 문이 없다. 문서·주석의 언급은 허용한다(불변식을
     설명하려면 이름을 써야 한다). 잡아야 할 것은 언급이 아니라 실제 import 다.
  ② 동적 — 별도 인터프리터에서 import 했을 때 `sys.modules` 에 rclpy 가 없다. 이쪽이 간접
     의존(다른 모듈을 거쳐 딸려오는 경우)까지 잡는 진짜 그물이다.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

#: `import rclpy` · `from rclpy.x import y` 를 잡는다(문자열 언급은 잡지 않는다).
_RCLPY_IMPORT = re.compile(r"^\s*(?:import\s+rclpy|from\s+rclpy[.\s])", re.MULTILINE)

#: `rclpy` 를 절대 끌어오면 안 되는 Phase 1 모듈.
PHASE1_MODULES = ("sysfs", "ringlog", "thresholds", "sampler")

_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_DIR = _PACKAGE_ROOT / "system_health"


@pytest.mark.parametrize("module", PHASE1_MODULES)
def test_source_has_no_rclpy_import_statement(module):
    source = (_SOURCE_DIR / f"{module}.py").read_text(encoding="utf-8")
    found = _RCLPY_IMPORT.search(source)
    assert found is None, (
        f"{module}.py 가 rclpy 를 import 한다 ({found.group(0).strip()!r}) — "
        "Phase 1 은 ROS 무의존이다"
    )


def test_the_import_detector_actually_detects():
    # 검출기가 망가지면 위 테스트가 조용히 통과해 불변식이 무력화된다.
    assert _RCLPY_IMPORT.search("import rclpy\n")
    assert _RCLPY_IMPORT.search("from rclpy.node import Node\n")
    assert _RCLPY_IMPORT.search("    import rclpy\n")
    assert _RCLPY_IMPORT.search("from rclpy import init\n")
    assert not _RCLPY_IMPORT.search("# rclpy 를 import 하지 않는다\n")
    assert not _RCLPY_IMPORT.search('"""rclpy 무의존."""\n')


def test_package_init_does_not_import_submodules_eagerly():
    # __init__ 이 Phase 2 브리지를 자동 import 하면 Phase 1 의 ROS 무의존이 깨진다.
    source = (_SOURCE_DIR / "__init__.py").read_text(encoding="utf-8")
    assert "import" not in source.split('"""')[-1], "__init__ 은 어떤 모듈도 import 하지 않는다"


@pytest.mark.parametrize("module", PHASE1_MODULES)
def test_importing_module_does_not_load_rclpy(module):
    code = (
        "import sys;"
        f"import system_health.{module};"
        "sys.exit(1 if 'rclpy' in sys.modules else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(_PACKAGE_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"system_health.{module} import 시 rclpy 가 적재됐다.\n{result.stderr}"
    )
