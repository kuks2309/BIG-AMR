# -*- coding: utf-8 -*-
"""What material a station's output is: type, attribute and drum type.

WHY THIS EXISTS. Material was minted with a LOT id and nothing else, so every
roll in the simulator was a thing nobody could describe. Three consequences,
none of them cosmetic:

  * CCS manual §1.3 refuses to feed a machine from a loading area holding
    material whose type and attribute are not recorded. With nothing recorded,
    `records.racks_fit_to_feed` answers "no" for every area in the plant and
    can never answer anything else — the rule is present and permanently
    inert.
  * `MaterialAttribute` and the rotation rules (§1.3's bright/dark face must
    match, rotation may be fixed by turning the pallet 180°) have nothing to
    operate on.
  * The map draws every payload the same grey, because size comes from the
    drum type and colour from the face.

THE MODEL IS THE CUSTOMER'S, THE VALUES ARE OURS. §1.3 and §4.6.5 both say a
machine has a **configured required material type and attribute** — so
"a station has a material profile" is their design, not our invention. What we
do not have is the configuration itself: nobody has told us which machine wants
which attribute. So `simulator_profile()` assigns them, and it is marked
⚠ INVENTED for that reason.

The assignment is deterministic and stable — the same station always gives the
same answer, across restarts and across runs — because a profile that changed
under a running line would make every selection rule non-reproducible and every
bug unrepeatable.
"""

from .material import KNOWN_DRUM_TYPES, MaterialAttribute


class MaterialProfile:
    """Station -> what its material is.

    A station with no entry and no default describes nothing, and that is a
    real state rather than an error: it is exactly the case §1.3 excludes, and
    the simulator must be able to produce it on purpose.
    """

    def __init__(self, by_station=None, default=None):
        self._by_station = dict(by_station or {})
        self._default = default

    def describe(self, station, kind="roll"):
        """The three fields `records.register_material` takes, or an empty
        dict when we cannot say.

        ⚠ THE FIELD NAMES ARE THE MATERIAL RECORD'S, not the rack's. The same
        two facts are called `attribute` / `drum_type` on a Material and
        `material_attribute` / `bobbin_type` on a RackSlot. This describes a
        MATERIAL, so it uses the material's names and `register_material(
        **describe(...))` works directly. Callers writing to a rack translate,
        which `pda.bind_to_rack` and `job_store._hand_identity_to` already do.

        That mismatch cost a live run on 2026-08-28: the profile returned the
        rack's names, every mint raised TypeError inside the monitor's
        try/except, and the simulator ran for five minutes creating no material
        at all while reporting nothing worse than "step failed".

        AN EMPTY BOBBIN IS A BARE CORE. It has a drum type — that is a property
        of the core itself — but no face and no material type, because there is
        no material on it. Describing one as though it carried material would
        put a face on a cardboard tube, and §1.3 would then feed a machine on
        the strength of it.
        """
        found = self._by_station.get(station, self._default)
        if not found:
            return {}
        if kind == "bobbin":
            return {"drum_type": found.get("drum_type")}
        return dict(found)

    def requires(self, station):
        """What material this station WANTS, or None if we were not told.

        CCS manual §4.6.5 puts the requested material type and attribute in
        MACHINE CONFIGURATION, and §1.3 reads it back before feeding: there
        must be material "whose attribute has the same bright/dark face".

        The same entry answers both questions, and that is not a shortcut. A
        station's profile is what material belongs there — produced at an
        unload port, required at a load port — so one description covers both
        ends of the same machine. When the real configuration arrives it may
        split them, and this is where it would.
        """
        found = self._by_station.get(station, self._default)
        if not found:
            return None
        return found.get("attribute")

    def stations(self):
        return sorted(self._by_station)


def simulator_profile(stations):
    """⚠ INVENTED — a plausible profile for every station in our plant.

    NOT customer data. Nobody has told us which machine requires which
    attribute, and this stands in so that the rules which read it can be
    exercised and the map can be read. Replace it wholesale when the real
    machine configuration arrives; nothing else needs to change.

    Deterministic by design. The attribute and drum type come from the
    station's position in a sorted list, so the same station always gets the
    same answer — across restarts, across runs, and in tests. A profile that
    varied would make every selection rule non-reproducible and every bug
    unrepeatable, which is a high price for looking more lifelike.

    All four attributes and all four drum types appear, because a profile that
    only ever produced one value would leave the matching rules untested — the
    face must match and the rotation may differ, and neither can be exercised
    by a plant where everything is 亮面顺时针.
    """
    attributes = list(MaterialAttribute)
    profile = {}
    for i, station in enumerate(sorted(stations)):
        profile[station] = {
            # The customer's material type is an INT in their table. Ours is
            # derived from the station so a reader can see where a roll came
            # from; it is a stand-in for their code, not a claim about it.
            "material_type": 300 + (i % 8),
            # `attribute`, not `material_attribute` — see `describe`.
            "attribute": attributes[i % len(attributes)],
            "drum_type": KNOWN_DRUM_TYPES[i % len(KNOWN_DRUM_TYPES)],
        }
    return MaterialProfile(profile)
