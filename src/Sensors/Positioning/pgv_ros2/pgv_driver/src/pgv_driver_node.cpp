// Pepperl+Fuchs PGV...-F200/-F200A...-R4-V19 읽기 헤드 ROS2 드라이버.
// RS-485 8-E-1 (매뉴얼 §2.2) 로 위치 응답을 폴링해 pgv/position 으로 발행하고,
// 방향 결정·색 선택 텔레그램을 서비스로 노출한다.
#include <fcntl.h>
#include <poll.h>
#include <termios.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <string>

#include "pgv_driver/pgv_protocol.hpp"
#include "pgv_interfaces/msg/pgv_position.hpp"
#include "pgv_interfaces/srv/set_color.hpp"
#include "pgv_interfaces/srv/set_direction.hpp"
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

namespace
{
// 매뉴얼 §2.2 지원 전송률 중 Linux termios 가 정의하는 것만.
// 76800 bit/s 는 장치는 지원하나 termios 상수가 없어 제외.
const std::map<int, speed_t> kBaudMap = {
    {38400, B38400},
    {57600, B57600},
    {115200, B115200},
    {230400, B230400},
};
}  // namespace

class PgvDriver : public rclcpp::Node
{
  public:
    PgvDriver() : Node("pgv_driver")
    {
        declare_parameter("serial_port", "/dev/ttyUSB0");
        declare_parameter("baudrate", 115200);  // 장치 preset (매뉴얼 §2.2)
        declare_parameter("address", 0);        // 읽기 헤드 주소 0..3
        declare_parameter("poll_rate_hz", 20.0);
        declare_parameter("serial_timeout_ms", 50);
        // 스케일은 장치 설정(코드 카드/Vision Configurator)과 일치해야 한다.
        // 위치 0.1/1/10 mm (§6.1.3), 각도 0.1/0.2/0.5/1 ° (§3.2) — 공장 preset 은 매뉴얼에 없음.
        declare_parameter("position_resolution_mm", 0.1);
        declare_parameter("angle_resolution_deg", 0.1);
        declare_parameter("frame_id", "pgv_link");
        // 기동 시 자동 방향 결정 — **전원 인가 후 이 명령이 없으면 장치는 error code 5**
        // 를 내고 위치를 일절 판독하지 않는다(매뉴얼 §4.1, Table 5.4). 서비스 수동 호출에
        // 의존하면 재부팅·센서 전원 재인가 때마다 조용히 계측 불능이 된다.
        // -1 = 자동 전송 안 함(수동 서비스만), 0..3 = Direction 값(3 = 직진).
        declare_parameter("startup_direction", 3);
        // error code 5 를 관측하면 자동으로 방향을 재전송한다(센서만 전원 재인가된 경우).
        declare_parameter("auto_recover_direction", true);
        declare_parameter("direction_retry_period_s", 2.0);

        serial_port_ = get_parameter("serial_port").as_string();
        baudrate_ = static_cast<int>(get_parameter("baudrate").as_int());
        address_ = static_cast<uint8_t>(get_parameter("address").as_int() &
                                        pgv_protocol::kMaxAddress);
        timeout_ms_ = static_cast<int>(get_parameter("serial_timeout_ms").as_int());
        position_resolution_mm_ = get_parameter("position_resolution_mm").as_double();
        angle_resolution_deg_ = get_parameter("angle_resolution_deg").as_double();
        frame_id_ = get_parameter("frame_id").as_string();
        startup_direction_ = static_cast<int>(get_parameter("startup_direction").as_int());
        auto_recover_direction_ = get_parameter("auto_recover_direction").as_bool();
        direction_retry_period_s_ = get_parameter("direction_retry_period_s").as_double();

        // QoS: RELIABLE (SensorData 깊이 유지) — RELIABLE 발행자는 RELIABLE·BEST_EFFORT
        // 구독자 모두와 호환되므로 제어기/로거 어느 쪽 기본 QoS 로도 수신 가능
        // (iahrs_driver 와 동일한 선택 근거).
        position_pub_ = create_publisher<pgv_interfaces::msg::PgvPosition>(
            "pgv/position", rclcpp::SensorDataQoS().reliable());

        set_direction_srv_ = create_service<pgv_interfaces::srv::SetDirection>(
            "pgv/set_direction",
            std::bind(&PgvDriver::onSetDirection, this, std::placeholders::_1,
                      std::placeholders::_2));
        set_color_srv_ = create_service<pgv_interfaces::srv::SetColor>(
            "pgv/set_color",
            std::bind(&PgvDriver::onSetColor, this, std::placeholders::_1,
                      std::placeholders::_2));

        serialOpen();

        // 폴링 시작 **전에** 방향을 정한다 — 순서가 반대면 첫 프레임들이 전부 error 5 다.
        if (fd_ >= 0 && startup_direction_ >= 0 && startup_direction_ <= 3)
        {
            std::uint8_t applied = 0;
            if (applyDirection(static_cast<std::uint8_t>(startup_direction_), applied))
            {
                RCLCPP_INFO(get_logger(), "기동 방향 결정: 요청 %d → 적용 %u",
                            startup_direction_, applied);
            }
            else
            {
                RCLCPP_WARN(get_logger(),
                            "기동 방향 결정 실패 — 장치가 error code 5 로 남는다. "
                            "auto_recover_direction 이 참이면 폴링 중 재시도한다");
            }
        }

        const double rate = get_parameter("poll_rate_hz").as_double();
        const auto period =
            std::chrono::duration<double>(rate > 0.0 ? 1.0 / rate : 0.05);
        poll_timer_ = create_wall_timer(
            std::chrono::duration_cast<std::chrono::nanoseconds>(period),
            std::bind(&PgvDriver::pollTimer, this));
    }

    ~PgvDriver() override
    {
        if (fd_ >= 0)
        {
            close(fd_);
        }
    }

  private:
    bool serialOpen()
    {
        const auto it = kBaudMap.find(baudrate_);
        if (it == kBaudMap.end())
        {
            RCLCPP_FATAL(get_logger(),
                         "baudrate %d 미지원 — 38400/57600/115200/230400 중 선택", baudrate_);
            return false;
        }

        fd_ = open(serial_port_.c_str(), O_RDWR | O_NOCTTY);
        if (fd_ < 0)
        {
            RCLCPP_ERROR(get_logger(), "시리얼 개방 실패: %s (%s)", serial_port_.c_str(),
                         strerror(errno));
            return false;
        }

        termios tio{};
        if (tcgetattr(fd_, &tio) != 0)
        {
            RCLCPP_ERROR(get_logger(), "tcgetattr 실패: %s", strerror(errno));
            close(fd_);
            fd_ = -1;
            return false;
        }
        cfmakeraw(&tio);
        // 8-E-1 (매뉴얼 §2.2): 8 데이터 비트 + 짝수 패리티 + 정지 1비트
        tio.c_cflag |= CS8 | PARENB | CREAD | CLOCAL;
        tio.c_cflag &= ~static_cast<tcflag_t>(PARODD | CSTOPB | CRTSCTS);
        // 패리티 오류 바이트는 폐기 — 잔여 오염은 프레임 XOR 검사가 걸러낸다
        tio.c_iflag |= INPCK | IGNPAR;
        tio.c_cc[VMIN] = 0;
        tio.c_cc[VTIME] = 0;
        cfsetispeed(&tio, it->second);
        cfsetospeed(&tio, it->second);
        if (tcsetattr(fd_, TCSANOW, &tio) != 0)
        {
            RCLCPP_ERROR(get_logger(), "tcsetattr 실패: %s", strerror(errno));
            close(fd_);
            fd_ = -1;
            return false;
        }
        tcflush(fd_, TCIOFLUSH);
        RCLCPP_INFO(get_logger(), "PGV 시리얼 개방: %s @ %d 8E1, addr=%u",
                    serial_port_.c_str(), baudrate_, address_);
        return true;
    }

    // 요청 1건 송신 후 rsp_len 바이트를 마감시한 내 수신. 폴링 타이머·서비스가
    // 같은 버스를 쓰므로 mutex 로 트랜잭션을 직렬화한다.
    bool transact(const std::uint8_t *req, std::size_t req_len, std::uint8_t *rsp,
                  std::size_t rsp_len)
    {
        std::lock_guard<std::mutex> lock(io_mutex_);
        if (fd_ < 0 && !serialOpen())
        {
            return false;
        }

        tcflush(fd_, TCIFLUSH);
        if (write(fd_, req, req_len) != static_cast<ssize_t>(req_len))
        {
            RCLCPP_WARN(get_logger(), "요청 송신 실패: %s", strerror(errno));
            close(fd_);
            fd_ = -1;  // 다음 트랜잭션에서 재개방
            return false;
        }

        std::size_t got = 0;
        const auto deadline =
            std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms_);
        while (got < rsp_len)
        {
            const auto remain = std::chrono::duration_cast<std::chrono::milliseconds>(
                deadline - std::chrono::steady_clock::now());
            if (remain.count() <= 0)
            {
                return false;  // 타임아웃 — 무응답 또는 부분 수신
            }
            pollfd pfd{fd_, POLLIN, 0};
            const int pr = poll(&pfd, 1, static_cast<int>(remain.count()));
            if (pr < 0)
            {
                RCLCPP_WARN(get_logger(), "poll 실패: %s", strerror(errno));
                return false;
            }
            if (pr == 0)
            {
                continue;  // 루프 상단에서 마감시한 판정
            }
            const ssize_t n = read(fd_, rsp + got, rsp_len - got);
            if (n < 0)
            {
                RCLCPP_WARN(get_logger(), "수신 실패: %s", strerror(errno));
                return false;
            }
            got += static_cast<std::size_t>(n);
        }
        return true;
    }

    void pollTimer()
    {
        const auto req = pgv_protocol::makePositionRequest(address_);
        std::uint8_t rsp[pgv_protocol::kPositionResponseLen];
        if (!transact(req.data(), req.size(), rsp, sizeof(rsp)))
        {
            ++fail_count_;
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                                 "위치 응답 없음 (연속 %zu회)", fail_count_);
            return;
        }

        pgv_protocol::PositionFrame frame{};
        const auto result = pgv_protocol::parsePositionResponse(rsp, sizeof(rsp), frame);
        if (result != pgv_protocol::ParseResult::kOk)
        {
            ++fail_count_;
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                                 "위치 응답 파싱 실패 (code=%d, 연속 %zu회)",
                                 static_cast<int>(result), fail_count_);
            return;
        }
        if (frame.address != address_)
        {
            ++fail_count_;
            RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000,
                                 "응답 주소 불일치: %u (기대 %u)", frame.address, address_);
            return;
        }
        fail_count_ = 0;
        position_pub_->publish(toMsg(frame));
        maybeRecoverDirection(frame);
    }

    /// `error code 5`(방향 미결정)를 관측하면 방향을 재전송한다.
    /// 센서만 전원이 재인가되면 장치는 방향을 잊고 판독을 멈추는데, 그 상태는 통신 정상
    /// (응답 20 Hz)이라 무응답 경고에 걸리지 않는다 — 이 경로가 없으면 조용히 계측 불능이다.
    void maybeRecoverDirection(const pgv_protocol::PositionFrame &f)
    {
        if (!auto_recover_direction_ || !f.error ||
            f.error_code != pgv_protocol::kErrNoDirection)
        {
            return;
        }
        const auto t = now();
        if (last_direction_retry_.nanoseconds() != 0 &&
            (t - last_direction_retry_).seconds() < direction_retry_period_s_)
        {
            return;
        }
        last_direction_retry_ = t;
        const int dir = (last_direction_ >= 0) ? last_direction_ : startup_direction_;
        if (dir < 0 || dir > 3)
        {
            return;
        }
        std::uint8_t applied = 0;
        if (applyDirection(static_cast<std::uint8_t>(dir), applied))
        {
            RCLCPP_WARN(get_logger(),
                        "error code 5(방향 미결정) 관측 — 방향 %d 재전송, 적용 %u", dir, applied);
        }
    }

    pgv_interfaces::msg::PgvPosition toMsg(const pgv_protocol::PositionFrame &f)
    {
        pgv_interfaces::msg::PgvPosition m;
        m.header.stamp = now();
        m.header.frame_id = frame_id_;

        m.tag_detected = f.tag_detected;
        m.no_lane = f.no_lane;
        m.no_position = f.no_position;
        m.repair_tape = f.repair_tape;
        m.lane_count = f.lane_count;

        m.x_raw = f.x;
        m.y_raw = f.y;
        m.angle_raw = f.angle;
        m.x_position_mm = f.error ? 0.0 : f.x * position_resolution_mm_;
        m.y_offset_mm = f.y * position_resolution_mm_;
        m.angle_deg = f.angle * angle_resolution_deg_;

        m.tag_number = f.tag_number;
        m.cc1_detected = f.cc1;
        m.cc2_detected = f.cc2;
        m.control_code1 = f.control_code1;
        m.control_code2 = f.control_code2;
        m.orientation1 = f.orientation1;
        m.orientation2 = f.orientation2;
        m.side1 = f.side1;
        m.side2 = f.side2;

        m.left_lane_selected = f.lane_left;
        m.right_lane_selected = f.lane_right;

        m.warning = f.warning;
        m.warning_bits = f.warning_bits;
        m.error = f.error;
        m.error_code = f.error_code;
        return m;
    }

    /// 방향 결정 텔레그램 1회 왕복. 기동 자동 전송과 서비스가 **같은 출처**를 쓴다 —
    /// 두 벌로 두면 한쪽만 고쳐져 갈라진다.
    bool applyDirection(std::uint8_t direction, std::uint8_t &applied)
    {
        applied = 0;
        if (direction > 3)
        {
            RCLCPP_ERROR(get_logger(), "direction=%u 범위 밖 (0..3)", direction);
            return false;
        }
        const auto telegram = pgv_protocol::makeDirectionRequest(
            static_cast<pgv_protocol::Direction>(direction), address_);
        std::uint8_t buf[pgv_protocol::kDirectionResponseLen];
        if (!transact(telegram.data(), telegram.size(), buf, sizeof(buf)))
        {
            RCLCPP_ERROR(get_logger(), "방향 결정 응답 없음");
            return false;
        }
        std::uint8_t dir_bits = 0;
        if (pgv_protocol::parseDirectionResponse(buf, sizeof(buf), dir_bits) !=
            pgv_protocol::ParseResult::kOk)
        {
            RCLCPP_ERROR(get_logger(), "방향 결정 응답 파싱 실패");
            return false;
        }
        applied = dir_bits;
        last_direction_ = direction;
        return true;
    }

    void onSetDirection(const std::shared_ptr<pgv_interfaces::srv::SetDirection::Request> req,
                        std::shared_ptr<pgv_interfaces::srv::SetDirection::Response> rsp)
    {
        std::uint8_t applied = 0;
        rsp->success = applyDirection(req->direction, applied);
        rsp->applied = applied;
        if (rsp->success)
        {
            RCLCPP_INFO(get_logger(), "방향 결정: 요청 %u → 적용 %u", req->direction, applied);
        }
    }

    void onSetColor(const std::shared_ptr<pgv_interfaces::srv::SetColor::Request> req,
                    std::shared_ptr<pgv_interfaces::srv::SetColor::Response> rsp)
    {
        rsp->success = false;
        if (req->color != 1 && req->color != 2 && req->color != 4)
        {
            RCLCPP_ERROR(get_logger(), "color=%u 는 BLUE=1/GREEN=2/RED=4 중 하나여야 함",
                         req->color);
            return;
        }
        const auto telegram = pgv_protocol::makeColorRequest(
            static_cast<pgv_protocol::Color>(req->color), address_);
        std::uint8_t buf[pgv_protocol::kColorResponseLen];
        if (!transact(telegram.data(), telegram.size(), buf, sizeof(buf)))
        {
            RCLCPP_ERROR(get_logger(), "색 선택 응답 없음");
            return;
        }
        std::uint8_t color_bits = 0;
        if (pgv_protocol::parseColorResponse(buf, sizeof(buf), color_bits) !=
                pgv_protocol::ParseResult::kOk ||
            color_bits != req->color)
        {
            RCLCPP_ERROR(get_logger(), "색 선택 확인 실패 (응답 비트 %u)", color_bits);
            return;
        }
        rsp->success = true;
        RCLCPP_INFO(get_logger(), "색 선택 적용: %u", req->color);
    }

    std::string serial_port_;
    int baudrate_{115200};
    std::uint8_t address_{0};
    int timeout_ms_{50};
    double position_resolution_mm_{0.1};
    double angle_resolution_deg_{0.1};
    std::string frame_id_;

    int fd_{-1};
    std::mutex io_mutex_;
    std::size_t fail_count_{0};
    int startup_direction_{3};
    bool auto_recover_direction_{true};
    double direction_retry_period_s_{2.0};
    int last_direction_{-1};            // 마지막으로 적용에 성공한 방향(재전송 기준)
    rclcpp::Time last_direction_retry_{0, 0, RCL_ROS_TIME};

    rclcpp::Publisher<pgv_interfaces::msg::PgvPosition>::SharedPtr position_pub_;
    rclcpp::Service<pgv_interfaces::srv::SetDirection>::SharedPtr set_direction_srv_;
    rclcpp::Service<pgv_interfaces::srv::SetColor>::SharedPtr set_color_srv_;
    rclcpp::TimerBase::SharedPtr poll_timer_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<PgvDriver>());
    rclcpp::shutdown();
    return 0;
}
