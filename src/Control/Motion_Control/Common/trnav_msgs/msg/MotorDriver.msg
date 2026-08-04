# motor_state: "RUNNING", "IDLE", "ALARM"
# motor_alarm_code: motor alarm code

# uint16[] slave_id
# uint8[] slave_channel
# string[] state
# int16[] alarm_code
# int32[] position;
# int16[] velocity;
# int16[] torque;
# uint8[] upper_limits;
# uint8[] lower_limits;
# uint16 axis_alarm_codes;

# # Define a message for a single channel
# int32 position
# float32 velocity
# ---
# # Define a message for a single motor driver
# int32 motor_driver_id
# ChannelStatus[] channels
# ---
# # Define the message for multiple motor drivers
# MotorDriver[] motor_drivers

# # Define the structure for each motor driver within the message
# MotorDriver.msg
# ---
# state: "RUNNING", "NOTREADY", "ALARM", "READY"
# alarm_code: motor alarm code

int32 motor_driver_id
string state
uint16 alarm_code
int32 position
int32 velocity
int16 amps
uint16 voltage
uint8 forward_limit
uint8 reverse_limit
uint8 home_comp
uint8 homing