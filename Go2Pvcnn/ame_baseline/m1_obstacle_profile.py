"""Single source of truth for the fixed M1 obstacle course geometry."""

# Obstacles are centered on the measured M1 wheel tracks and alternate sides.
# Six fixed small obstacles form the ordered serial-crossing curriculum.
M1_FIXED_SMALL_OBSTACLE_LOCAL_XY = (
    (0.55, 0.215), (1.10, -0.215), (1.65, 0.215),
    (2.20, -0.215), (2.75, 0.215), (3.30, -0.215),
)
M1_FIXED_LARGE_OBSTACLE_LOCAL_XY = ((1.5, -1.0), (3.2, 1.0))
M1_SMALL_OBSTACLE_DIAMETER_M = 0.05
M1_DEFAULT_SMALL_OBSTACLE_HEIGHT_M = 0.10
