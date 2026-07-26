# Platform-agnostic wheel command array
# Replaces legacy tc_msgs/WheelMotor (QD-hardcoded) for the motion_mux pipeline.
#
# Publisher/subscriber contract:
#   - Each WheelSet in wheels[] represents one physical drive wheel
#   - Array order and length are platform-specific (defined in platform YAML)
#   - Publisher and consumer must agree on order (mux enforces via config)

std_msgs/Header header
WheelSet[] wheels
