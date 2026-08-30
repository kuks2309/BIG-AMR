#!/usr/bin/env python3
# A5 verification: (1) drawio XML well-formed, (2) no dangling edge source/target,
# (3) mermaid nodes/edges == drawio nodes/edges 1:1
import re, sys, xml.etree.ElementTree as ET

# 경로는 이 스크립트 위치 기준으로 해석한다(저장소 어디서 실행해도 동일 결과).
#   .mmd  : 같은 폴더(flow-src/)
#   drawio: 상위 폴더의 2026-07-28-flow.drawio
import os as _os
BASE = _os.path.dirname(_os.path.abspath(__file__))
DRAWIO = _os.path.join(_os.path.dirname(BASE), "2026-07-28-flow.drawio")

print("=== (1) XML well-formed check: xml.etree.ElementTree.parse ===")
tree = ET.parse(DRAWIO)
root = tree.getroot()
print("OK  root tag =", root.tag, " diagrams =", len(root.findall("diagram")))

fail = 0
total_v = total_e = 0
for dia in root.findall("diagram"):
    name = dia.get("name")
    r = dia.find("mxGraphModel/root")
    cells = r.findall("mxCell")
    vertices = {c.get("id") for c in cells if c.get("vertex") == "1"}
    edges = [(c.get("id"), c.get("source"), c.get("target")) for c in cells if c.get("edge") == "1"]
    total_v += len(vertices); total_e += len(edges)

    print("\n=== diagram: %s ===" % name)
    print("  vertices=%d  edges=%d  (plus root cells id=0,id=1)" % (len(vertices), len(edges)))

    # (2) dangling check
    dangling = [(eid, s, t) for eid, s, t in edges if s not in vertices or t not in vertices]
    print("  (2) dangling edges (source/target not a real box): %d" % len(dangling))
    if dangling:
        fail = 1
        for d in dangling[:10]:
            print("      DANGLING", d)

    # geometry / style shape check
    bad_style = [c.get("id") for c in cells if c.get("vertex") == "1"
                 and c.get("style") != "rounded=0;whiteSpace=wrap;html=1;"]
    bad_geo = [c.get("id") for c in cells if c.get("vertex") == "1"
               and c.find("mxGeometry") is None]
    bad_estyle = [c.get("id") for c in cells if c.get("edge") == "1"
                  and c.get("style") != "endArrow=classic;html=1;"]
    print("  box style deviations=%d  missing geometry=%d  edge style deviations=%d"
          % (len(bad_style), len(bad_geo), len(bad_estyle)))
    if bad_style or bad_geo or bad_estyle:
        fail = 1

    # (3) mermaid 1:1
    mmf = BASE + "/mermaid-%s.mmd" % name
    txt = open(mmf).read()
    lines = [l.strip() for l in txt.splitlines()[1:] if l.strip()]
    m_nodes = set(); m_edges = []
    for l in lines:
        m = re.match(r'^state ".*" as ([A-Za-z0-9_]+)$', l)
        if m:
            m_nodes.add(m.group(1)); continue
        m = re.match(r'^([A-Za-z0-9_]+)\s*-->\s*([A-Za-z0-9_]+)(\s*:.*)?$', l)
        if m:
            m_edges.append((m.group(1), m.group(2))); continue
        m = re.match(r'^([A-Za-z0-9_]+)\s*-->\|".*"\|\s*([A-Za-z0-9_]+)$', l)
        if m:
            m_edges.append((m.group(1), m.group(2))); continue
        m = re.match(r'^([A-Za-z0-9_]+)(\{"|\(\["|\[/"|\[")', l)
        if m:
            m_nodes.add(m.group(1)); continue
        print("      UNPARSED MERMAID LINE:", l); fail = 1
    d_edges = [(s, t) for _, s, t in edges]
    print("  (3) mermaid nodes=%d drawio boxes=%d  equal=%s"
          % (len(m_nodes), len(vertices), m_nodes == vertices))
    print("      mermaid edges=%d drawio edges=%d  multiset equal=%s"
          % (len(m_edges), len(d_edges), sorted(m_edges) == sorted(d_edges)))
    if m_nodes != vertices:
        fail = 1
        print("      only in mermaid:", sorted(m_nodes - vertices))
        print("      only in drawio :", sorted(vertices - m_nodes))
    if sorted(m_edges) != sorted(d_edges):
        fail = 1
        print("      diff:", set(m_edges) ^ set(d_edges))

print("\n=== TOTAL: boxes=%d arrows=%d ===" % (total_v, total_e))
print("RESULT:", "FAIL" if fail else "PASS - XML well-formed, 0 dangling, mermaid<->drawio 1:1")
sys.exit(fail)
