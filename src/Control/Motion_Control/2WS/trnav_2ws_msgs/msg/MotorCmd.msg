# Per-motor low-level command (CiA 402 abstraction).
# Produced by motor_cmd_translator, consumed by canopen_motor_driver / canopen_sim.
# Units are raw device units — NOT SI.
uint8 motor_id        # 1=walk_front, 2=walk_rear, 3=steer_front, 4=steer_rear
                      # (platform-agnostic; id↔role mapping lives in translator YAML)
uint8 mode            # 0=DISABLED, 1=VELOCITY, 2=POSITION, 3=TORQUE
int32 target_vel      # 0.1 rpm units (CiA 402 0x60FF Target velocity, profile velocity mode)
int32 target_pos      # pulse units (CiA 402 0x607A Target position, profile position mode)
int32 profile_vel     # profile velocity for POSITION mode
                      # (CiA 402 0x6081, 0.1 rpm or vendor pulse/s — driver passes through)

uint8 MODE_DISABLED = 0
uint8 MODE_VELOCITY = 1
uint8 MODE_POSITION = 2
uint8 MODE_TORQUE   = 3
