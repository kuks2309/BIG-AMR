"""Source selection — a destination may be served by any qualifying upstream.

`FEEDS` pairs each destination with one machine, which is a good default because
it spreads four destinations across four sources. It is a bad *rule*: when the
paired machine is empty the destination used to wait, even with three siblings
holding finished material.

These tests pin the ranking and the fallback, because both are policy decisions
someone will want to change and neither is obvious from reading the code.
"""

from csm import plant


def test_rack_is_offered_before_fresh_material():
    """Otherwise a rack only ever fills — there is always something newer."""
    for dest in ("GRV1_LD", "CTR1_LD", "SLT_LD1"):
        cands = plant.sources_for(dest)
        seg = plant.segment_of_station(dest)
        assert cands[:len(seg["buffer"])] == seg["buffer"], dest


def test_paired_machine_comes_before_its_siblings():
    """FEEDS' pairing survives as a preference, spreading load across sources."""
    cands = plant.sources_for("CTR3_LD")
    assert plant.FEEDS["CTR3_LD"] == "GRV3_ULD"
    non_buffer = [c for c in cands if not c.startswith("WIP_")]
    assert non_buffer[0] == "GRV3_ULD"
    assert set(non_buffer) == {f"GRV{i}_ULD" for i in range(1, 5)}


def test_every_destination_can_fall_back_to_a_sibling():
    """The whole point: one empty machine must not stall a destination."""
    for seg in plant.SEGMENTS:
        for dest in seg["to"]:
            cands = plant.sources_for(dest)
            assert len(cands) > len(seg["buffer"]), dest
            assert set(seg["from"]) <= set(cands), dest


def test_segment_c_now_has_a_rack():
    """It had `buffer: []`, so two of its four job types were impossible."""
    seg = next(s for s in plant.SEGMENTS if s["name"] == "C")
    assert seg["buffer"], "segment C must have a WIP rack"
    for port in seg["buffer"]:
        assert plant.STATIONS[port]["kind"] == "BUFFER"


def test_rack_capacity_is_slots_not_docks():
    """The deck counts slots; the layout gives far fewer places to stand."""
    assert plant.BUFFER_CAPACITY == {"WIP_GRV": 2, "WIP_CTR": 13, "WIP_SLT": 30}
    docks = [n for n, s in plant.STATIONS.items() if s["kind"] == "BUFFER"]
    assert len(docks) == 6, "two access ports per rack"
    assert plant.BUFFER_CAPACITY["WIP_SLT"] > len(docks)


def test_station_and_robot_segment_lookups_are_distinct():
    """They were both called segment_of; one silently shadowed the other."""
    assert plant.segment_of_station("CTR1_LD")["name"] == "B"
    assert plant.segment_of("amr3")["name"] == "C"
    assert plant.segment_of_station("amr3") is None
