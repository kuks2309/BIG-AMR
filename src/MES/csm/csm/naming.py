"""naming — the job and task names from the SW Workshop #2 deck.

SOURCE. `TR_F Project SW 워크샵 2차.pptx` slide 4 (the definitions) and slide 6
(three worked examples), presented 2026-08-20 and discussed 2026-08-21. The deck
is held outside this repository — it is internal material and this repository is
public — at `References/local/customer/`.

    Job   JB_[공정명]_[AGV Type]_[요청 장비]_[From 장비]_[To 장비]_[대상물]
    Task  TK_[공정명]_[AGV Type]_[Task Name]

Slide 6's examples, which are what this module is checked against:

    JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL
    JB_CELL_LOWBIGA_GRVPRTLD_WIPGP_GRVPRNTLD_ROLL
    JB_CELL_LOWBIGA_GRVPRTLD_GRVPRTLD_ASRS_BOBBIN

THE NAME IS THE ID, WITH A COUNTER
==================================

Decided 2026-08-21. The deck's name is not unique on its own — the first example
above is every ASRS-to-Gravure roll delivery there will ever be — and
`AcsOrder.id` must be "unique and stable" because every later operation names the
order by it. So `job_id` appends a four-digit counter:

    JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL_0001

The gain is that an id explains itself. A fleet-controller log line, one of our
records, or an error message says the line, the AGV class, who asked, both ends
and what is moving, without a lookup against anything.

⚠ **ONE THING THE ID STILL DOES NOT SAY: WHICH MACHINE.** `GRV1_LD` and
`GRV4_LD` both render as `GRVPRTLD`, because the deck's codes are per PROCESS.
A job's `from_instance` / `to_instance` carry that and the id has no slot for it.

Adding it — `GRVPRTLD1` — would make the id genuinely complete, and it is a one
line change to `station_code`. It is not made here because the format is Dr.
Shim's, and extending someone's convention without asking is how two
incompatible spellings appear. Open question for 2026-08-24.
"""

from .job import Carried

#: THE LINE. `CELL` in every example the deck gives. A second line would need
#: its own code and nobody has named one, so this is a default rather than a
#: constant pretending to be a discovery.
DEFAULT_PROCESS = "CELL"

#: Leg -> the deck's AGV type code.
#:
#: The legs are `plant.SEGMENTS`; the tonnage is `plant.py`'s header, from the
#: system deck [S16]. Slide 6 spells leg A's code `LOWBIGA`, and slide 4's task
#: example spells the same class `LOWTBIGA`. **The deck disagrees with itself.**
#: `LOWBIGA` is CANONICAL here, decided 2026-08-21: it appears three times
#: against the other's once, and it matches the `LOWBIGA` / `LOWBIGB` pair the
#: CSM specification rev01 §3 already uses. The deck is to be corrected to
#: match, rather than this code following the deck's inconsistency.
AGV_TYPES = {
    "A": "LOWBIGA",     # 1.5T-Big AGV A  x2
    "B": "LOWBIGB",     # 1.5T-Big AGV B  x2   (extrapolated from A)
    "C": "HIGHBIG",     # 3.5T-Big AGV    x6   (slide 4: "HIGHBIG")
}

#: Our station names -> the deck's process codes.
#:
#: CONFIRMED means the code appears in the deck. PROPOSED means it does not and
#: this is our extension by the same pattern — the deck only ever worked the
#: gravure examples, so coater, slitter and two of the three WIP racks have
#: never been written down by anyone.
STATION_CODES = {
    # -- confirmed by the deck -------------------------------------------
    "ASRS":     "ASRS",         # slide 6, twice
    "GRV_LD":   "GRVPRTLD",     # slide 6. The deck also spells this GRVPRNTLD
                                # once and GRAVPRTLD on slide 4 — three
                                # spellings of one code. GRVPRTLD is CANONICAL,
                                # decided 2026-08-21; the deck is to be
                                # corrected, not followed.
    "WIP_GRV":  "WIPGP",        # slide 6
    # -- proposed, by the same pattern -----------------------------------
    "GRV_ULD":  "GRVPRTULD",
    "CTR_LD":   "COATLD",
    "CTR_ULD":  "COATULD",
    "SLT_LD":   "SLTLD",
    "SLT_ULD":  "SLTULD",
    "WIP_CTR":  "WIPCT",
    "WIP_SLT":  "WIPSL",
}

#: Which of the above the deck actually shows. Kept as data rather than a
#: comment so a test can assert we have not quietly promoted a guess.
CONFIRMED_CODES = frozenset({"ASRS", "GRV_LD", "WIP_GRV"})

#: What a job carries -> the deck's object code.
OBJECT_CODES = {
    Carried.ROLL: "ROLL",
    Carried.BOBBIN: "BOBBIN",
}

#: When a station cannot be coded at all. Loud on purpose: a silently wrong
#: name is worse than an obviously missing one, and this is the string that
#: will appear in a log if the plant grows a station this table has not met.
UNKNOWN = "UNKNOWN"


def station_code(station):
    """Our station name -> the deck's process code.

    `GRV1_LD` and `GRV4_LD` both give `GRVPRTLD`; see the module note.
    """
    if not station:
        return UNKNOWN
    if station in STATION_CODES:          # ASRS, and anything already exact
        return STATION_CODES[station]

    family, _, rest = station.partition("_")

    # WIP racks are WIP_<family>_<n>; the family is the second part.
    if family == "WIP":
        sub = rest.split("_")[0]
        return STATION_CODES.get(f"WIP_{sub}", UNKNOWN)

    # Machine ports are <FAMILY><n>_<LD|ULD>, and the slitter is SLT_LD<n>,
    # so the port word is whichever part starts with LD or ULD.
    family = family.rstrip("0123456789")
    for part in rest.split("_"):
        port = part.rstrip("0123456789")
        if port in ("LD", "ULD"):
            return STATION_CODES.get(f"{family}_{port}", UNKNOWN)
    return STATION_CODES.get(family, UNKNOWN)


def agv_type(segment):
    """Leg name -> AGV type code. `plant.segment_of_station` gives the leg."""
    return AGV_TYPES.get(segment, UNKNOWN)


def job_name(job, segment, requester=None, process=DEFAULT_PROCESS):
    """The deck's job name for one job.

    :param job: anything with `from_station`, `to_station` and `carries`
    :param segment: the leg working it — `A`, `B` or `C`
    :param requester: the station that asked. Defaults to the source, which is
        what two of slide 6's three examples do; the third is requested by the
        destination, so it cannot be derived and must be passed when known.
    :param process: the line. `CELL` everywhere the deck looks.

    Returns a DESCRIPTION, not an identifier. See the module docstring.
    """
    carries = getattr(job, "carries", None)
    return "_".join((
        "JB",
        process,
        agv_type(segment),
        station_code(requester or job.from_station),
        station_code(job.from_station),
        station_code(job.to_station),
        OBJECT_CODES.get(carries, UNKNOWN),
    ))


def job_id(job, segment, sequence, requester=None, process=DEFAULT_PROCESS):
    """The job's identifier: the deck's name, plus a counter that makes it unique.

        JB_CELL_LOWBIGA_ASRS_ASRS_GRVPRTLD_ROLL_0001

    :param sequence: a number unique within this CSM's lifetime.

    THE COUNTER IS FOUR DIGITS AND DOES NOT WRAP. It is `%04d`, so it pads to
    four and then simply grows — a run that raises more than 9,999 jobs gets
    five digits and stays unique, which matters more than staying aligned.
    """
    return f"{job_name(job, segment, requester, process)}_{sequence:04d}"


def task_name(kind, segment, process=DEFAULT_PROCESS):
    """The deck's task name. `kind` is a `TaskKind` or its name."""
    name = getattr(kind, "name", None) or str(kind)
    return "_".join(("TK", process, agv_type(segment), name))


# ---------------------------------------------------------------------------
# TO CONFIRM WITH DR. SHIM — all three are cheap for him to answer and
# expensive for us to guess:
#
#   1. Should the id carry the MACHINE NUMBER? `GRVPRTLD1` rather than
#      `GRVPRTLD`. Without it an id cannot say which of the four gravures,
#      which is the one thing a self-describing id still cannot tell you.
#   2. The codes for coater, slitter and the coater/slitter WIP racks have
#      never been written down. The ones above are our extension.
#   3. For information: the deck's spelling inconsistencies (GRVPRTLD /
#      GRVPRNTLD / GRAVPRTLD, LOWBIGA / LOWTBIGA) are resolved here to the
#      first of each. The deck should be corrected to match.
# ---------------------------------------------------------------------------
