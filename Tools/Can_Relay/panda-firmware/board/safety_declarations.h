#define GET_BIT(msg, b) (((msg)->data[((b) / 8U)] >> ((b) % 8U)) & 0x1U)
#define GET_BYTE(msg, b) ((msg)->data[(b)])
#define GET_BYTES_04(msg) ((msg)->data[0] | ((msg)->data[1] << 8U) | ((msg)->data[2] << 16U) | ((msg)->data[3] << 24U))
#define GET_BYTES_48(msg) ((msg)->data[4] | ((msg)->data[5] << 8U) | ((msg)->data[6] << 16U) | ((msg)->data[7] << 24U))
#define GET_FLAG(value, mask) (((__typeof__(mask))(value) & (mask)) == (mask))

const int MAX_WRONG_COUNTERS = 5;
const uint8_t MAX_MISSED_MSGS = 10U;

struct sample_t {
  int values[6];
  int min;
  int max;
} sample_t_default = {.values = {0}, .min = 0, .max = 0};

struct lookup_t {
  float x[3];
  float y[3];
};

typedef struct {
  int addr;
  int bus;
  int len;
} CanMsg;

typedef struct {
  const int addr;
  const int bus;
  const int len;
  const bool check_checksum;
  const uint8_t max_counter;
  const uint32_t expected_timestep;
} CanMsgCheck;

typedef struct {

  const CanMsgCheck msg[3];

  bool msg_seen;
  int index;
  bool valid_checksum;
  int wrong_counters;
  uint8_t last_counter;
  uint32_t last_timestamp;
  bool lagging;
} AddrCheckStruct;

typedef struct {
  AddrCheckStruct *check;
  int len;
} addr_checks;

int safety_rx_hook(CANPacket_t *to_push);
int safety_tx_hook(CANPacket_t *to_send);
int safety_tx_lin_hook(int lin_num, uint8_t *data, int len);
uint32_t get_ts_elapsed(uint32_t ts, uint32_t ts_last);
int to_signed(int d, int bits);
void update_sample(struct sample_t *sample, int sample_new);
bool max_limit_check(int val, const int MAX, const int MIN);
bool dist_to_meas_check(int val, int val_last, struct sample_t *val_meas,
  const int MAX_RATE_UP, const int MAX_RATE_DOWN, const int MAX_ERROR);
bool driver_limit_check(int val, int val_last, struct sample_t *val_driver,
  const int MAX, const int MAX_RATE_UP, const int MAX_RATE_DOWN,
  const int MAX_ALLOWANCE, const int DRIVER_FACTOR);
bool get_longitudinal_allowed(void);
bool rt_rate_limit_check(int val, int val_last, const int MAX_RT_DELTA);
float interpolate(struct lookup_t xy, float x);
void gen_crc_lookup_table_8(uint8_t poly, uint8_t crc_lut[]);
void gen_crc_lookup_table_16(uint16_t poly, uint16_t crc_lut[]);
bool msg_allowed(CANPacket_t *to_send, const CanMsg msg_list[], int len);
int get_addr_check_index(CANPacket_t *to_push, AddrCheckStruct addr_list[], const int len);
void update_counter(AddrCheckStruct addr_list[], int index, uint8_t counter);
void update_addr_timestamp(AddrCheckStruct addr_list[], int index);
bool is_msg_valid(AddrCheckStruct addr_list[], int index);
bool addr_safety_check(CANPacket_t *to_push,
                       const addr_checks *rx_checks,
                       uint32_t (*get_checksum)(CANPacket_t *to_push),
                       uint32_t (*compute_checksum)(CANPacket_t *to_push),
                       uint8_t (*get_counter)(CANPacket_t *to_push));
void generic_rx_checks(bool stock_ecu_detected);
void relay_malfunction_set(void);
void relay_malfunction_reset(void);

typedef const addr_checks* (*safety_hook_init)(uint16_t param);
typedef int (*rx_hook)(CANPacket_t *to_push);
typedef int (*tx_hook)(CANPacket_t *to_send, bool longitudinal_allowed);
typedef int (*tx_lin_hook)(int lin_num, uint8_t *data, int len);
typedef int (*fwd_hook)(int bus_num, CANPacket_t *to_fwd);
void can_send(CANPacket_t *to_push, uint8_t bus_number, bool skip_tx_hook);

typedef struct {
  safety_hook_init init;
  rx_hook rx;
  tx_hook tx;
  tx_lin_hook tx_lin;
  fwd_hook fwd;
} safety_hooks;

void safety_tick(const addr_checks *addr_checks);

bool controls_allowed = false;
bool relay_malfunction = false;
bool gas_interceptor_detected = false;
int gas_interceptor_prev = 0;
bool gas_pressed = false;
bool gas_pressed_prev = false;
bool brake_pressed = false;
bool brake_pressed_prev = false;
bool cruise_engaged_prev = false;
float vehicle_speed = 0;
bool vehicle_moving = false;
bool acc_main_on = false;
int cruise_button_prev = 0;

int desired_torque_last = 0;
int rt_torque_last = 0;
struct sample_t torque_meas;
struct sample_t torque_driver;
uint32_t ts_last = 0;

uint32_t ts_angle_last = 0;
int desired_angle_last = 0;
struct sample_t angle_meas;

#define ALT_EXP_DISABLE_DISENGAGE_ON_GAS 1

#define ALT_EXP_DISABLE_STOCK_AEB 2

#define ALT_EXP_RAISE_LONGITUDINAL_LIMITS_TO_ISO_MAX 8

int alternative_experience = 0;

uint32_t safety_mode_cnt = 0U;

const uint32_t RELAY_TRNS_TIMEOUT = 1U;
