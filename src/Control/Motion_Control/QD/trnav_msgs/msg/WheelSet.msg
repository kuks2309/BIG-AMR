# Per-wheel motion command (platform-agnostic)
# Used as element of WheelSetArray.wheels[]
#
# Platform interpretation:
#   QD diagonal : wheels[0]=W1(front-left), wheels[1]=W2(rear-right)
#   DD          : wheels[0]=Left, wheels[1]=Right, steering always 0
#   4WS         : wheels[0..3]=FL,FR,RL,RR each with independent velocity+steering
#   Ackermann   : wheels[0..3] with rear steering=0
#
# Array order is defined by platform YAML, not message itself.

float64 velocity    # m/s, drive speed (+forward, -reverse)
float64 steering    # rad, steering angle (0 for non-steering wheels)
