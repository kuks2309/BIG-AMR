###bottom_agv_st && top_agv_st######
# STATUS_SAFETY 0
# STATUS_WARNING 1
# STATUS_DANGEROUS 2

uint8 raw_data_safety_st # combine raw_lidar_front_st and raw_lidar_rear_st
uint8 raw_lidar_front_st
uint8 raw_lidar_rear_st 
uint8 field_data_safety_st # combine field_lidar_front_st and field_lidar_rear_st
uint8 field_lidar_front_st
uint8 field_lidar_rear_st 
uint8 navi_lidar_front_field
uint8 navi_lidar_rear_field