# # Define the message for multiple motor drivers
# MotorDriver[] motor_drivers

# # Define the structure for each motor driver within the message
# MotorDriver.msg
# ---
# int32 motor_driver_id
# ChannelStatus[] channels

# # Define the structure for each channel within the message
# ChannelStatus.msg
# ---
# string state
# uint16[] alarm_code
# int32 position
# int16 velocity
# int16 amps
# uint8 forward_limit
# uint8 reverse_limit
# uint8 home_comp
# uint8 homing


int8 NOTREADY = 0
int8 HOMING = 1
int8 HOMECOMP = 2
int8 ALARM = 3

MotorDriver[] motor_drivers
int16 driving_status