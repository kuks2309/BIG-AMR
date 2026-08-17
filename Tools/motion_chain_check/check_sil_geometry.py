#!/usr/bin/env python3
"""SIL 런치가 플랜트에 **자기 플랫폼** 기하 정본을 얹는지 검사한다.

런치 기술을 실제로 해석해서(문자열 grep 이 아니라) `translate_sim_odom_node` 에 붙는
파라미터 파일 목록을 뽑고, 그 안에 기하 정본이 있는지·플랫폼이 맞는지 본다.
"""
import importlib.util
import os
import sys

try:
    from launch import LaunchContext
    from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
except ImportError:  # ROS 환경이 없으면 런치를 해석할 수 없다 — 통과로 위장하지 않는다
    print("ROS 2 launch 모듈이 없다 — `source /opt/ros/humble/setup.bash` 후 다시 실행하라",
          file=sys.stderr)
    raise SystemExit(2)

# 저장소 루트는 이 파일 위치에서 되짚는다 — 워크트리마다 경로가 다르므로 박아 두지 않는다.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

EXPECT = {"2WS": "robot_geometry_2ws.yaml", "QD": "robot_geometry_qd.yaml"}


def platform_of(path):
    if "/2WS/" in path:
        return "2WS"
    if "/QD/" in path:
        return "QD"
    return None


def param_files(node, context):
    """Node 에 붙은 파라미터 파일을 **실제 경로로 풀어서** 돌려준다.

    문자열 grep 이 아니라 런치가 실제로 만들 경로를 본다 — 치환이 어디를 가리키는지가 요점이다."""
    out = []
    for entry in getattr(node, "_Node__parameters", ()) or ():
        pf = getattr(entry, "param_file", None)
        if pf is None:
            continue
        try:
            out.append(str(perform_substitutions(context, normalize_to_list_of_substitutions(pf))))
        except Exception as e:
            out.append(f"<해석실패:{type(e).__name__}>")
    return out


def find_plant_nodes(entities, acc):
    for e in entities:
        cls = type(e).__name__
        if cls == "Node" and getattr(e, "_Node__node_executable", "") == "translate_sim_odom_node":
            acc.append(e)
        for attr in ("entities", "_entities"):
            sub = getattr(e, attr, None)
            if isinstance(sub, (list, tuple)):
                find_plant_nodes(sub, acc)
    return acc


def main():
    launches = []
    for dirpath, dirnames, names in os.walk(os.path.join(ROOT, "src")):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "install", "log")]
        for n in names:
            if n.endswith(".launch.py"):
                p = os.path.join(dirpath, n)
                if "translate_sim_odom_node" in open(p, errors="replace").read():
                    launches.append(p)

    bad = 0
    for p in sorted(launches):
        rel = os.path.relpath(p, ROOT)
        spec = importlib.util.spec_from_file_location("lch", p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            ld = mod.generate_launch_description()
        except Exception as e:
            print(f"  ⚠ {rel}: 런치 해석 실패 {type(e).__name__}: {e}")
            bad += 1
            continue
        context = LaunchContext()
        for e in ld.entities:
            if type(e).__name__ == "DeclareLaunchArgument":
                try:
                    e.visit(context)
                except Exception:
                    pass
        nodes = find_plant_nodes(ld.entities, [])
        if not nodes:
            print(f"  ⚠ {rel}: 플랜트 노드를 찾지 못했다")
            bad += 1
            continue
        for node in nodes:
            texts = param_files(node, context)
            geoms = [os.path.basename(t) for t in texts
                     if os.path.basename(t).startswith("robot_geometry_")]
            plat = platform_of(p)
            want = EXPECT.get(plat)
            if not geoms:
                # 런치 인자로 고르는 경우(패키지 자체 런치)는 인자 기본값이 있으면 통과
                if any("geometry_file" in str(t) for t in texts):
                    print(f"  OK   {rel}: 런치 인자로 선택")
                    continue
                print(f"  ❌ {rel}: 기하 정본 미주입")
                bad += 1
            elif want and geoms[0] != want:
                print(f"  ❌ {rel}: 플랫폼 불일치 — {geoms[0]} (기대 {want})")
                bad += 1
            else:
                print(f"  OK   {rel}: {geoms[0]}")

    print(f"\n-- 런치 {len(launches)}개 · 불합격 {bad}건")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
