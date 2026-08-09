// json_min — 재생 도구 전용 최소 JSON 리더 (헤더 온리, 표준 라이브러리만).
//
// 목적: `rawmap_to_jsonl.py` 가 낸 JSONL 레코드와 `*.meta.json` 사이드카를 읽는 것뿐이다.
//   외부 JSON 라이브러리를 끌어오면 이 도구 하나 때문에 저장소 의존성이 늘어난다.
//
// 지원 범위: RFC 8259 의 값 문법 전부(object/array/string/number/true/false/null).
//   미지원: 중복 키(뒤엣것 채택), 문자열 이스케이프 중 `\uXXXX` 는 BMP 단일 코드유닛만 UTF-8 로 변환한다
//   (서러게이트 쌍 미결합). 우리 입력은 순수 ASCII 라 실제로 쓰이지 않는 경로다.
//
// 수치는 `std::strtod` 로 읽는다 — Python `json.dumps` 가 내는 최단 왕복 표기를 **무손실**로 복원한다.
#ifndef SEER_RAWMAP_REPLAY_JSON_MIN_HPP
#define SEER_RAWMAP_REPLAY_JSON_MIN_HPP

#include <cstdlib>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace json_min
{

/// 파싱 실패. 메시지에 입력 오프셋(바이트)을 담는다.
class ParseError : public std::runtime_error
{
  public:
    explicit ParseError(const std::string &what) : std::runtime_error(what)
    {
    }
};

class Value;
using Object = std::map<std::string, Value>;
using Array = std::vector<Value>;

/// JSON 값 하나. 복사 가능(레코드가 작아 성능 문제 없음).
class Value
{
  public:
    enum class Type
    {
        kNull,
        kBool,
        kNumber,
        kString,
        kArray,
        kObject
    };

    Value() = default;

    Type type() const
    {
        return type_;
    }
    bool isNull() const
    {
        return type_ == Type::kNull;
    }
    bool isNumber() const
    {
        return type_ == Type::kNumber;
    }
    bool isArray() const
    {
        return type_ == Type::kArray;
    }
    bool isObject() const
    {
        return type_ == Type::kObject;
    }
    bool isString() const
    {
        return type_ == Type::kString;
    }

    /// @return 수치값. 타입이 number 가 아니면 `ParseError`.
    double asNumber(const std::string &context = "") const
    {
        if (type_ != Type::kNumber)
        {
            throw ParseError(context + ": 수치가 아니다");
        }
        return number_;
    }

    bool asBool(const std::string &context = "") const
    {
        if (type_ != Type::kBool)
        {
            throw ParseError(context + ": 참거짓이 아니다");
        }
        return bool_;
    }

    const std::string &asString(const std::string &context = "") const
    {
        if (type_ != Type::kString)
        {
            throw ParseError(context + ": 문자열이 아니다");
        }
        return string_;
    }

    const Array &asArray(const std::string &context = "") const
    {
        if (type_ != Type::kArray)
        {
            throw ParseError(context + ": 배열이 아니다");
        }
        return array_;
    }

    const Object &asObject(const std::string &context = "") const
    {
        if (type_ != Type::kObject)
        {
            throw ParseError(context + ": 객체가 아니다");
        }
        return object_;
    }

    /// 객체 멤버 조회. 없으면 `nullptr`. 객체가 아니어도 `nullptr`.
    const Value *find(const std::string &key) const
    {
        if (type_ != Type::kObject)
        {
            return nullptr;
        }
        const auto it = object_.find(key);
        return it == object_.end() ? nullptr : &it->second;
    }

    /// 배열을 `double` 벡터로. 원소가 수치가 아니면 `ParseError`.
    std::vector<double> asNumberVector(const std::string &context = "") const
    {
        const Array &a = asArray(context);
        std::vector<double> out;
        out.reserve(a.size());
        for (std::size_t i = 0; i < a.size(); ++i)
        {
            out.push_back(a[i].asNumber(context + "[" + std::to_string(i) + "]"));
        }
        return out;
    }

    static Value makeNumber(double v)
    {
        Value x;
        x.type_ = Type::kNumber;
        x.number_ = v;
        return x;
    }
    static Value makeBool(bool v)
    {
        Value x;
        x.type_ = Type::kBool;
        x.bool_ = v;
        return x;
    }
    static Value makeString(std::string v)
    {
        Value x;
        x.type_ = Type::kString;
        x.string_ = std::move(v);
        return x;
    }
    static Value makeArray(Array v)
    {
        Value x;
        x.type_ = Type::kArray;
        x.array_ = std::move(v);
        return x;
    }
    static Value makeObject(Object v)
    {
        Value x;
        x.type_ = Type::kObject;
        x.object_ = std::move(v);
        return x;
    }

  private:
    Type type_ = Type::kNull;
    bool bool_ = false;
    double number_ = 0.0;
    std::string string_;
    Array array_;
    Object object_;
};

namespace detail
{

/// 재귀 하강 파서. 입력 전체를 소유하지 않고 참조만 본다(수명은 호출자 책임).
class Parser
{
  public:
    explicit Parser(const std::string &text) : text_(text)
    {
    }

    /// 값 하나를 읽고, 뒤에 공백 외 잔여물이 있으면 오류.
    Value parseDocument()
    {
        skipSpace();
        Value v = parseValue(0);
        skipSpace();
        if (pos_ != text_.size())
        {
            fail("문서 끝에 잔여 입력");
        }
        return v;
    }

  private:
    /// 중첩 깊이 상한. 없으면 악의적/손상 입력이 스택을 태운다.
    static constexpr int kMaxDepth = 64;

    [[noreturn]] void fail(const std::string &msg) const
    {
        throw ParseError("JSON offset " + std::to_string(pos_) + ": " + msg);
    }

    bool atEnd() const
    {
        return pos_ >= text_.size();
    }

    char peek() const
    {
        if (atEnd())
        {
            fail("입력이 갑자기 끝났다");
        }
        return text_[pos_];
    }

    void skipSpace()
    {
        while (!atEnd())
        {
            const char c = text_[pos_];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r')
            {
                ++pos_;
            }
            else
            {
                break;
            }
        }
    }

    void expect(char c)
    {
        if (atEnd() || text_[pos_] != c)
        {
            fail(std::string("'") + c + "' 를 기대했다");
        }
        ++pos_;
    }

    bool literal(const char *lit)
    {
        const std::size_t n = std::char_traits<char>::length(lit);
        if (text_.compare(pos_, n, lit) == 0)
        {
            pos_ += n;
            return true;
        }
        return false;
    }

    Value parseValue(int depth)
    {
        if (depth > kMaxDepth)
        {
            fail("중첩이 너무 깊다");
        }
        skipSpace();
        const char c = peek();
        switch (c)
        {
        case '{':
            return parseObject(depth);
        case '[':
            return parseArray(depth);
        case '"':
            return Value::makeString(parseString());
        case 't':
            if (literal("true"))
            {
                return Value::makeBool(true);
            }
            fail("true 가 아니다");
        case 'f':
            if (literal("false"))
            {
                return Value::makeBool(false);
            }
            fail("false 가 아니다");
        case 'n':
            if (literal("null"))
            {
                return Value();
            }
            fail("null 이 아니다");
        default:
            return parseNumber();
        }
    }

    Value parseObject(int depth)
    {
        expect('{');
        Object obj;
        skipSpace();
        if (peek() == '}')
        {
            ++pos_;
            return Value::makeObject(std::move(obj));
        }
        for (;;)
        {
            skipSpace();
            std::string key = parseString();
            skipSpace();
            expect(':');
            obj[std::move(key)] = parseValue(depth + 1);
            skipSpace();
            const char c = peek();
            if (c == ',')
            {
                ++pos_;
                continue;
            }
            if (c == '}')
            {
                ++pos_;
                return Value::makeObject(std::move(obj));
            }
            fail("객체에서 ',' 또는 '}' 를 기대했다");
        }
    }

    Value parseArray(int depth)
    {
        expect('[');
        Array arr;
        skipSpace();
        if (peek() == ']')
        {
            ++pos_;
            return Value::makeArray(std::move(arr));
        }
        for (;;)
        {
            arr.push_back(parseValue(depth + 1));
            skipSpace();
            const char c = peek();
            if (c == ',')
            {
                ++pos_;
                continue;
            }
            if (c == ']')
            {
                ++pos_;
                return Value::makeArray(std::move(arr));
            }
            fail("배열에서 ',' 또는 ']' 를 기대했다");
        }
    }

    std::string parseString()
    {
        expect('"');
        std::string out;
        for (;;)
        {
            if (atEnd())
            {
                fail("문자열이 닫히지 않았다");
            }
            const char c = text_[pos_++];
            if (c == '"')
            {
                return out;
            }
            if (c != '\\')
            {
                out.push_back(c);
                continue;
            }
            if (atEnd())
            {
                fail("이스케이프가 끊겼다");
            }
            const char e = text_[pos_++];
            switch (e)
            {
            case '"':
                out.push_back('"');
                break;
            case '\\':
                out.push_back('\\');
                break;
            case '/':
                out.push_back('/');
                break;
            case 'b':
                out.push_back('\b');
                break;
            case 'f':
                out.push_back('\f');
                break;
            case 'n':
                out.push_back('\n');
                break;
            case 'r':
                out.push_back('\r');
                break;
            case 't':
                out.push_back('\t');
                break;
            case 'u':
                appendUtf8(parseHex4(), out);
                break;
            default:
                fail("알 수 없는 이스케이프");
            }
        }
    }

    unsigned parseHex4()
    {
        if (pos_ + 4 > text_.size())
        {
            fail("\\u 뒤 4자리가 모자란다");
        }
        unsigned v = 0;
        for (int i = 0; i < 4; ++i)
        {
            const char c = text_[pos_++];
            v <<= 4;
            if (c >= '0' && c <= '9')
            {
                v |= static_cast<unsigned>(c - '0');
            }
            else if (c >= 'a' && c <= 'f')
            {
                v |= static_cast<unsigned>(c - 'a' + 10);
            }
            else if (c >= 'A' && c <= 'F')
            {
                v |= static_cast<unsigned>(c - 'A' + 10);
            }
            else
            {
                fail("16진 숫자가 아니다");
            }
        }
        return v;
    }

    /// BMP 코드포인트 하나를 UTF-8 로 인코딩해 `dst` 뒤에 붙인다.
    static void appendUtf8(unsigned cp, std::string &dst)
    {
        if (cp < 0x80u)
        {
            dst.push_back(static_cast<char>(cp));
        }
        else if (cp < 0x800u)
        {
            dst.push_back(static_cast<char>(0xC0u | (cp >> 6)));
            dst.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
        }
        else
        {
            dst.push_back(static_cast<char>(0xE0u | (cp >> 12)));
            dst.push_back(static_cast<char>(0x80u | ((cp >> 6) & 0x3Fu)));
            dst.push_back(static_cast<char>(0x80u | (cp & 0x3Fu)));
        }
    }

    Value parseNumber()
    {
        const char *begin = text_.c_str() + pos_;
        char *end = nullptr;
        const double v = std::strtod(begin, &end);
        if (end == begin)
        {
            fail("수치가 아니다");
        }
        pos_ += static_cast<std::size_t>(end - begin);
        return Value::makeNumber(v);
    }

    const std::string &text_;
    std::size_t pos_ = 0;
};

} // namespace detail

/// 문자열 하나를 JSON 문서로 파싱한다.
///
/// @param text UTF-8 JSON 문서 (한 개의 최상위 값).
/// @return 파싱된 값.
/// @throws ParseError 문법 오류 시 (메시지에 바이트 오프셋 포함).
inline Value parse(const std::string &text)
{
    detail::Parser p(text);
    return p.parseDocument();
}

} // namespace json_min

#endif // SEER_RAWMAP_REPLAY_JSON_MIN_HPP
