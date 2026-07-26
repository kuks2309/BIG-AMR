# WheelMotorState.msg
# Complete state information for all wheel motors including encoder values and timestamps

std_msgs/Header header

# Encoder values (raw pulse counts from each motor)
int32 encoder_walk_front    # Front drive motor encoder (pulse)
int32 encoder_walk_rear     # Rear drive motor encoder (pulse)
int32 encoder_steer_front   # Front steering motor encoder (pulse)
int32 encoder_steer_rear    # Rear steering motor encoder (pulse)

# Calculated velocities and angles
float64 velocity_front      # Front wheel velocity (m/s)
float64 velocity_rear       # Rear wheel velocity (m/s)
float64 angle_front         # Front steering angle (rad)
float64 angle_rear          # Rear steering angle (rad)

# Motor status information
bool motor_ready            # All motors ready status
uint8 error_code            # Error code (0 = OK, non-zero = error)

# Error codes definition:
# 0: OK
# 1: Communication error
# 2: Motor driver error
# 3: Encoder error
# 4: Calibration required
