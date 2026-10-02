from __future__ import annotations

from ...domain.catalog import TechniqueCatalog
from ...domain.model import (\n    Band,\n    BottomBehavior,\n    EntityKind,\n    ExitDestination,\n    Grade,\n    Side,\n    TechniqueEntity,\n    TopBehavior,\n)


TOP_HIGH_MOUNT_CLIMB = "mount.top.high_mount_climb"
TOP_CROSSFACE_PRESSURE = "mount.top.crossface_pressure"
TOP_AMERICANA_ARM_ISOLATION = "mount.top.americana_arm_isolation"

BOTTOM_BRIDGE = "mount.bottom.bridge"
BOTTOM_ELBOW_KNEE_ESCAPE = "mount.bottom.elbow_knee_escape"
BOTTOM_TRAP_AND_ROLL_ESCAPE = "mount.bottom.trap_and_roll_escape"

TOP_RESPONSE_POST_AND_BASE = "mount.top_response.post_and_base"
TOP_RESPONSE_WIDE_MOUNT_BASE = "mount.top_response.wide_mount_base"
TOP_RESPONSE_HIP_FOLLOW_REPUMMEL = "mount.top_response.hip_follow_repummel"

BOTTOM_RESPONSE_FOREARM_FRAME = "mount.bottom_response.forearm_frame"
BOTTOM_RESPONSE_TURN_IN_RECOVERY = "mount.bottom_response.turn_in_recovery"
BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE = "mount.bottom_response.tight_elbow_arm_defense"


ENTITIES: tuple[TechniqueEntity, ...] = (
    TechniqueEntity(
        id=TOP_HIGH_MOUNT_CLIMB,
        kind=EntityKind.ACTION,
        side=Side.TOP,
        canonical_name="High Mount Climb",
        short_name="Climb High",
        legacy_name="Climb High",
        aliases=("Climb to High Mount", "Walk Knees High", "Knees to Armpits"),
        category="POSITIONAL_ADVANCE",
        description="Climb the knees and hips higher on the torso to improve Mount control.",
    ),
    TechniqueEntity(
        id=TOP_CROSSFACE_PRESSURE,
        kind=EntityKind.ACTION,
        side=Side.TOP,
        canonical_name="Crossface Pressure",
        short_name="Crossface",
        legacy_name="Pressure Shift",
        aliases=("Shoulder Pressure", "Crossface Control"),
        category="CONTROL",
        description="Use head-and-shoulder control to compromise alignment and hip movement.",
    ),
    TechniqueEntity(
        id=TOP_AMERICANA_ARM_ISOLATION,
        kind=EntityKind.ACTION,
        side=Side.TOP,
        canonical_name="Americana Arm Isolation",
        short_name="Americana Isolation",
        legacy_name="Arm Isolation",
        aliases=("Americana Setup", "Americana Isolation", "Bent-Arm Isolation", "Keylock Setup"),
        category="SUBMISSION_SETUP",
        description="Separate and control the arm in the bent-arm structure associated with an Americana attack.",
    ),
    TechniqueEntity(
        id=BOTTOM_BRIDGE,
        kind=EntityKind.ACTION,
        side=Side.BOTTOM,
        canonical_name="Bridge",
        short_name="Bridge",
        legacy_name="Bridge",
        aliases=("Hip Bridge", "Bridging", "Bridge to Create Space"),
        category="DISRUPTION",
        description="Elevate the hips to disrupt balance and create space without completing an escape.",
        escape_capable=False,
        special_rule="bridge_clamp",
    ),
    TechniqueEntity(
        id=BOTTOM_ELBOW_KNEE_ESCAPE,
        kind=EntityKind.ACTION,
        side=Side.BOTTOM,
        canonical_name="Elbow-Knee Escape",
        short_name="Elbow-Knee Escape",
        legacy_name="Elbow Escape",
        aliases=("Knee-Elbow Escape", "Knee-Elbow Mount Escape", "Shrimp Escape", "Mount Shrimp Escape"),
        category="ESCAPE",
        description="Frame, move the hips, and insert the knee to recover guard.",
        escape_capable=True,
        exit_map={
            Grade.SUCCESS: ExitDestination.HALF_GUARD,
            Grade.STRONG_SUCCESS: ExitDestination.OPEN_GUARD,
        },
        band_exit_overrides={
            (Grade.STRONG_SUCCESS, Band.STABLE): ExitDestination.HALF_GUARD,
        },
    ),
    TechniqueEntity(
        id=BOTTOM_TRAP_AND_ROLL_ESCAPE,
        kind=EntityKind.ACTION,
        side=Side.BOTTOM,
        canonical_name="Trap-and-Roll Escape",
        short_name="Trap-and-Roll",
        legacy_name="Trap-and-Roll",
        aliases=("Bridge-and-Roll", "Bridge-and-Roll Escape", "Upa", "Upa Escape"),
        category="ESCAPE",
        description="Remove a posting structure, bridge, and roll toward the compromised side.",
        escape_capable=True,
        exit_map={
            Grade.SUCCESS: ExitDestination.REVERSAL,
            Grade.STRONG_SUCCESS: ExitDestination.REVERSAL,
        },
    ),
    TechniqueEntity(
        id=TOP_RESPONSE_POST_AND_BASE,
        kind=EntityKind.RESPONSE,
        side=Side.TOP,
        canonical_name="Hand Post and Base",
        short_name="Post",
        legacy_name="Post",
        aliases=("Hand Post", "Post the Hand", "Post and Base", "Base Out"),
        category="BASE_DEFENSE",
        description="Establish a post and restore base against destabilization or a roll.",
    ),
    TechniqueEntity(
        id=TOP_RESPONSE_WIDE_MOUNT_BASE,
        kind=EntityKind.RESPONSE,
        side=Side.TOP,
        canonical_name="Wide Mount Base",
        short_name="Wide Base",
        legacy_name="Widen Base",
        aliases=("Widen Base", "Base Wide", "Lower the Base"),
        category="BASE_DEFENSE",
        description="Widen and lower the support structure of Mount to resist displacement.",
    ),
    TechniqueEntity(
        id=TOP_RESPONSE_HIP_FOLLOW_REPUMMEL,
        kind=EntityKind.RESPONSE,
        side=Side.TOP,
        canonical_name="Hip Follow and Knee Re-Pummel",
        short_name="Hip Follow",
        legacy_name="Follow Hips",
        aliases=(
            "Follow the Hips",
            "Knee Re-Pummel",
            "Follow and Re-Pummel",
            "Hip Tracking",
            "Repummel",
            "Hip Follow + Knee Re-Pummel",
            "Hip Follow & Knee Repummel",
        ),
        category="RETENTION_RESPONSE",
        description="Track the hips and re-pummel the knee to deny knee insertion and space recovery.",
    ),
    TechniqueEntity(
        id=BOTTOM_RESPONSE_FOREARM_FRAME,
        kind=EntityKind.RESPONSE,
        side=Side.BOTTOM,
        canonical_name="Forearm Frame",
        short_name="Frame",
        legacy_name="Frame",
        aliases=("Frame",),
        category="FRAME_DEFENSE",
        description="Use forearm skeletal structure to manage pressure and distance.",
    ),
    TechniqueEntity(
        id=BOTTOM_RESPONSE_TURN_IN_RECOVERY,
        kind=EntityKind.RESPONSE,
        side=Side.BOTTOM,
        canonical_name="Turn-In Recovery",
        short_name="Turn In",
        legacy_name="Turn In",
        aliases=("Turn-In", "Turn Toward", "Recover Alignment"),
        category="ALIGNMENT_DEFENSE",
        description="Turn toward Top to restore useful alignment rather than remain flattened or misaligned.",
    ),
    TechniqueEntity(
        id=BOTTOM_RESPONSE_TIGHT_ELBOW_ARM_DEFENSE,
        kind=EntityKind.RESPONSE,
        side=Side.BOTTOM,
        canonical_name="Tight-Elbow Arm Defense",
        short_name="Tight Elbows",
        legacy_name="Protect Arm",
        aliases=(
            "Arm Retraction",
            "Elbow Retraction",
            "Elbow-to-Ribs Defense",
            "Protect the Arm",
            "Tight-Elbow Defense",
        ),
        category="COMPACT_STRUCTURE_DEFENSE",
        description=(
            "Keep the elbows compact enough to resist the High Mount climb and protect against Americana "
            "isolation while leaving the head-and-shoulder line comparatively open to Crossface Pressure. "
            "This is narrower than a complete elbow-knee connection system."
        ),
    ),
)

MOUNT_CATALOG = TechniqueCatalog.build(ENTITIES)
ENTITY_BY_ID = MOUNT_CATALOG.by_id

TOP_ACTIONS = MOUNT_CATALOG.actions_for(Side.TOP)
BOTTOM_ACTIONS = MOUNT_CATALOG.actions_for(Side.BOTTOM)
TOP_RESPONSES = MOUNT_CATALOG.responses_for(Side.TOP)
BOTTOM_RESPONSES = MOUNT_CATALOG.responses_for(Side.BOTTOM)


def actions_for(side: Side) -> tuple[TechniqueEntity, ...]:
    return MOUNT_CATALOG.actions_for(side)


def responses_for(side: Side) -> tuple[TechniqueEntity, ...]:
    return MOUNT_CATALOG.responses_for(side)
