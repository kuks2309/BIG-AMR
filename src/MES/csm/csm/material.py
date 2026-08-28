"""What a roll IS, as far as the routing rules care.

`records.Material` holds identity and whereabouts. This holds the three things
CATL's own system ROUTES on, and which we did not have:

  * **material attribute** — bright or dark face, clockwise or anticlockwise
  * **drum type** — 360 / 430 / 500 / 580
  * **pallet capacity** — derived from the drum type, not stored beside it

TWO SOURCES AGREE ON ALL THREE, which is why they are here rather than guessed:
the CCS manual §4.6.5 (configuring a machine's requested attribute) and the rack
PLC variable table of 2026-08-19 (`Rack_To_PCS[7]`, `[8]`, `[3]`). Notes in
`References/local/ccs-manual-notes.md` §4 and `rack-plc-interface.md`.

WHY A MODULE AND NOT CONSTANTS IN records.py. Because `1` has to mean exactly
one thing. In their table `1` is "bright face, clockwise" in `MaterialAttribute`
and "no bobbin" in `TrayStatusA` and "available" in `StationEnable`. Threading
bare integers through the CSM is how those meanings get crossed.

WHAT THIS MODULE DOES NOT DO. It does not choose a source, and it does not know
what any machine wants — §4.6.5 puts the requested attribute in machine
configuration, which our adapters do not carry yet. `matches()` is the rule,
ready for the caller that will have both halves.
"""

from enum import Enum


class Face(Enum):
    """Which side of the foil is out. 亮面 / 暗面."""

    BRIGHT = "bright"
    DARK = "dark"


class Rotation(Enum):
    """Which way the roll is wound. 顺时针 / 逆时针."""

    CW = "clockwise"
    CCW = "anticlockwise"


class MaterialAttribute(Enum):
    """The customer's 1–4, and the two facts each one encodes.

    Their values, in their order: `1-亮面顺时针；2-亮面逆时针；3-暗面顺时针；
    4-暗面逆时针` (manual §4.6.5, identical in `Rack_To_PCS[7]`).

    THE ORDER IS NOT ARBITRARY and the pairing matters: 1↔2 and 3↔4 differ only
    in rotation, which is the difference a 180° turn erases. That is what makes
    `rotated()` a lookup rather than arithmetic.
    """

    BRIGHT_CW = 1
    BRIGHT_CCW = 2
    DARK_CW = 3
    DARK_CCW = 4

    @property
    def face(self):
        return Face.BRIGHT if self in (MaterialAttribute.BRIGHT_CW,
                                       MaterialAttribute.BRIGHT_CCW) else Face.DARK

    @property
    def rotation(self):
        return Rotation.CW if self in (MaterialAttribute.BRIGHT_CW,
                                       MaterialAttribute.DARK_CW) else Rotation.CCW

    def rotated(self):
        """The same face, wound the other way — what a 180° turn produces.

        Rotating the PALLET does not change which side of the foil faces out;
        it changes the direction the roll presents. So the face is invariant
        and the rotation flips, which is exactly the freedom §3.6 relies on.
        """
        return _ROTATED[self]

    def matches(self, required, rotatable=True):
        """Can this material serve a request for `required`?

        §3.6, and it is NOT equality:

          * **the face must match** — nothing turns a bright face into a dark one;
          * **the rotation need not**, because the pallet can be turned 180°,
            and "rotate then feed" is a first-class AGV task type (§3.8).

        `rotatable=False` for the material types configured non-rotatable
        (§4.6.11), where the attribute must match exactly.

        An unknown requirement is not a wildcard — see `attribute_matches`.
        """
        if required is None:
            return False
        if rotatable:
            return self.face is required.face
        return self is required


_ROTATED = {
    MaterialAttribute.BRIGHT_CW: MaterialAttribute.BRIGHT_CCW,
    MaterialAttribute.BRIGHT_CCW: MaterialAttribute.BRIGHT_CW,
    MaterialAttribute.DARK_CW: MaterialAttribute.DARK_CCW,
    MaterialAttribute.DARK_CCW: MaterialAttribute.DARK_CW,
}


def attribute_matches(have, required, rotatable=True):
    """`matches` that tolerates either side being unknown — by refusing.

    UNKNOWN IS NOT A WILDCARD. Material whose attribute nobody recorded may not
    be fed to a machine that asked for a particular face: the cost of waiting is
    a deferred call, and the cost of guessing is a machine loaded with the wrong
    side out. Their own system refuses on missing info rather than proceeding
    (§5.1, §6 item 5), and refuses to use a rack whose sensors disagree at all.

    ⚠ This is the OPPOSITE default to resting time, where unknown counts as
    READY. That asymmetry is deliberate: resting has a documented shipped
    default of 0 (§4.6.12, *"静置为非标准功能"*), so unknown there really does
    mean "not configured". Nothing says an unrecorded attribute means "any".
    """
    if have is None or required is None:
        return False
    return have.matches(required, rotatable=rotatable)


def needs_rotation(have, required, rotatable=True):
    """Must this pallet be TURNED 180° before it can serve `required`?

    §1.3 and §3.8. True only when all three hold:

      * it CAN serve the requirement — the face already matches, and nothing
        turns a bright face into a dark one;
      * the rotation differs, so it does not serve it as it stands;
      * the material type is rotatable (§4.6.11 configures some as not).

    FALSE WHEN IT ALREADY MATCHES, and false when it cannot serve the
    requirement at all. "Needs rotating" is not the answer to "this is the
    wrong material" — answering True there would send a robot to turn a pallet
    that is still useless afterwards, which is the expensive kind of wrong: a
    task, a docking and a machine still waiting.

    Unknown on either side is False, for the same reason `attribute_matches`
    refuses: an unrecorded attribute is not a wildcard, and we would be
    rotating on a guess.
    """
    if have is None or required is None or not rotatable:
        return False
    if have is required:
        return False                      # already exactly right
    return have.matches(required, rotatable=True)


#: At or above this drum type a pallet carries ONE bobbin; below it, two.
#: `Rack_To_PCS[8]`: "360, 430, 500, 580 — ≥500 single-bobbin pallet, <500
#: dual-bobbin pallet". The manual §4 says the same in the same words.
SINGLE_BOBBIN_FROM = 500

#: The drum types seen in the documents. NOT the domain — the field is an INT
#: in their table, so an unlisted value is possible and must still yield a
#: capacity rather than an error.
KNOWN_DRUM_TYPES = (360, 430, 500, 580)


def pallet_capacity(drum_type):
    """How many bobbins a pallet of this drum type carries. None if unknown.

    DERIVED, NEVER STORED. Keeping capacity as its own field lets it disagree
    with the drum type it is supposed to follow, and then two records describe
    the same pallet differently.
    """
    if drum_type is None:
        return None
    return 1 if drum_type >= SINGLE_BOBBIN_FROM else 2


def is_dual_pallet(drum_type):
    """True only when we know it is dual. Unknown is not dual."""
    return pallet_capacity(drum_type) == 2


class TrayStatus(Enum):
    """`Rack_To_PCS[3]` — what is on the pallet, all of it on a DUAL-slot tray."""

    NONE = 0                 # no pallet at all
    EMPTY_PALLET = 1         # a pallet, nothing on it
    SINGLE_EMPTY_BOBBIN = 2
    DOUBLE_EMPTY_BOBBIN = 3
    SINGLE_MATERIAL = 4
    DOUBLE_MATERIAL = 5

    @property
    def auto_transportable(self):
        """May the automatic flow move this?

        §2.2 and §6: a dual-slot pallet holding ONE roll is not auto-transported
        — a person must add the second or remove the single one. An EMPTY pallet
        is outside the automatic flow entirely: *"中控系统自动流程业务逻辑不含空
        托盘的流转"*.
        """
        return self in (TrayStatus.DOUBLE_MATERIAL,
                        TrayStatus.DOUBLE_EMPTY_BOBBIN)

    @property
    def returnable(self):
        """May this go back as the empty-bobbin return flow?

        §1.2.2: the exit pallet must carry DOUBLE bobbins of the matching type.
        A single empty bobbin is not enough, and this is one of the two states
        §6 item 6 tells a human to go and fix every day.
        """
        return self is TrayStatus.DOUBLE_EMPTY_BOBBIN


class TrayCondition(Enum):
    """Whether a tray reading is a tray state at all."""

    NORMAL = "normal"
    ERROR = "error"          # >900
    RESET = "reset"          # exactly 800


#: `TrayStatus` is an INT carrying two out-of-band values, and this is stated
#: outright in the source: ">900 means the rack is in error, and 800 is a
#: reset. So it is not a plain enum and must not be range-checked as one."
TRAY_RESET = 800
TRAY_ERROR_FROM = 900


def classify_tray(value):
    """`(TrayStatus | None, TrayCondition)`. Never raises, never guesses.

    A plain `IntEnum` would raise on 800 and 950. A range check would accept 950
    as a tray state, which is the worse failure: a rack reporting an error would
    read as a rack holding something.

    A caller that ignores the condition gets **None** for the status, so the
    failure mode of not reading this properly is "we do not know", not "we know
    something wrong".
    """
    if value is None:
        return None, TrayCondition.NORMAL
    if value >= TRAY_ERROR_FROM:
        return None, TrayCondition.ERROR
    if value == TRAY_RESET:
        return None, TrayCondition.RESET
    try:
        return TrayStatus(value), TrayCondition.NORMAL
    except ValueError:
        # In range but not a value they documented. Unknown, not an error —
        # their table may simply have grown.
        return None, TrayCondition.NORMAL


class SideStatus(Enum):
    """`TrayStatusA` / `TrayStatusB` — one side of the pallet."""

    NO_BOBBIN = 1
    EMPTY_BOBBIN = 2
    MATERIAL = 3


class MaterialState(Enum):
    """`Rack_To_PCS[12]` — 0 empty, 1 NG, 2 OK."""

    EMPTY = 0
    NG = 1
    OK = 2
