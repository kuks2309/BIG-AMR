# Per-motor low-level feedback (raw device units).
# Produced by canopen_motor_driver / canopen_sim, consumed by motor_cmd_translator.
uint8 motor_id
int32 fb_vel          # 0.1 rpm (CiA 402 0x606C Velocity actual value)
int32 fb_pos          # pulse   (CiA 402 0x6064 Position actual value)
uint16 error_code     # CiA 402 0x603F Error code (0 = no error)
int16 amps            # 0x6078 Current actual value
int16 voltage         # 0x6079 DC link circuit voltage
bool home_comp        # homing sequence completed
bool homing           # homing in progress
bool motor_enabled    # CiA 402 operation enable state
bool can_reset        # slave rebooted since last read
