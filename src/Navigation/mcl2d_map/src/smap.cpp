#include "mcl2d_map/smap.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>

namespace mcl2d
{
namespace
{

// ── 최소 JSON 파서 (재귀 하강) — object/array/string/number/bool/null 지원 ──
struct JValue
{
    enum Type
    {
        Null,
        Bool,
        Num,
        Str,
        Arr,
        Obj
    } type = Null;
    double num = 0.0;
    bool b = false;
    std::string str;
    std::vector<JValue> arr;
    std::vector<std::pair<std::string, JValue>> obj;

    const JValue *find(const std::string &key) const
    {
        for (const auto &kv : obj)
            if (kv.first == key)
                return &kv.second;
        return nullptr;
    }
    double numOr(double d) const
    {
        return type == Num ? num : d;
    }
};

class Parser
{
  public:
    explicit Parser(const std::string &s) : s_(s)
    {
    }
    bool parse(JValue &out)
    {
        skip();
        return value(out) && (skip(), true);
    }

  private:
    const std::string &s_;
    std::size_t i_ = 0;

    void skip()
    {
        while (i_ < s_.size())
        {
            char c = s_[i_];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r')
                ++i_;
            else
                break;
        }
    }
    bool value(JValue &v)
    {
        skip();
        if (i_ >= s_.size())
            return false;
        char c = s_[i_];
        if (c == '{')
            return object(v);
        if (c == '[')
            return array(v);
        if (c == '"')
        {
            v.type = JValue::Str;
            return string(v.str);
        }
        if (c == 't' || c == 'f')
            return boolean(v);
        if (c == 'n')
        {
            v.type = JValue::Null;
            return lit("null");
        }
        return number(v);
    }
    bool object(JValue &v)
    {
        v.type = JValue::Obj;
        ++i_; // {
        skip();
        if (i_ < s_.size() && s_[i_] == '}')
        {
            ++i_;
            return true;
        }
        while (true)
        {
            skip();
            if (i_ >= s_.size() || s_[i_] != '"')
                return false;
            std::string key;
            if (!string(key))
                return false;
            skip();
            if (i_ >= s_.size() || s_[i_] != ':')
                return false;
            ++i_;
            JValue child;
            if (!value(child))
                return false;
            v.obj.emplace_back(std::move(key), std::move(child));
            skip();
            if (i_ >= s_.size())
                return false;
            if (s_[i_] == ',')
            {
                ++i_;
                continue;
            }
            if (s_[i_] == '}')
            {
                ++i_;
                return true;
            }
            return false;
        }
    }
    bool array(JValue &v)
    {
        v.type = JValue::Arr;
        ++i_; // [
        skip();
        if (i_ < s_.size() && s_[i_] == ']')
        {
            ++i_;
            return true;
        }
        while (true)
        {
            JValue child;
            if (!value(child))
                return false;
            v.arr.push_back(std::move(child));
            skip();
            if (i_ >= s_.size())
                return false;
            if (s_[i_] == ',')
            {
                ++i_;
                continue;
            }
            if (s_[i_] == ']')
            {
                ++i_;
                return true;
            }
            return false;
        }
    }
    bool string(std::string &out)
    {
        ++i_; // opening "
        while (i_ < s_.size())
        {
            char c = s_[i_++];
            if (c == '"')
                return true;
            if (c == '\\')
            {
                if (i_ >= s_.size())
                    return false;
                char e = s_[i_++];
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
                case 'n':
                    out.push_back('\n');
                    break;
                case 't':
                    out.push_back('\t');
                    break;
                case 'r':
                    out.push_back('\r');
                    break;
                case 'b':
                    out.push_back('\b');
                    break;
                case 'f':
                    out.push_back('\f');
                    break;
                case 'u': { // \uXXXX — 4 hex 스킵(값은 미해석, 좌표엔 불필요)
                    for (int k = 0; k < 4 && i_ < s_.size(); ++k)
                        ++i_;
                    out.push_back('?');
                    break;
                }
                default:
                    out.push_back(e);
                }
            }
            else
            {
                out.push_back(c); // UTF-8 바이트 그대로 통과
            }
        }
        return false;
    }
    bool number(JValue &v)
    {
        std::size_t start = i_;
        while (i_ < s_.size())
        {
            char c = s_[i_];
            if ((c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E')
                ++i_;
            else
                break;
        }
        if (i_ == start)
            return false;
        v.type = JValue::Num;
        v.num = std::strtod(s_.substr(start, i_ - start).c_str(), nullptr);
        return true;
    }
    bool boolean(JValue &v)
    {
        v.type = JValue::Bool;
        if (s_[i_] == 't')
        {
            v.b = true;
            return lit("true");
        }
        v.b = false;
        return lit("false");
    }
    bool lit(const char *l)
    {
        for (std::size_t k = 0; l[k]; ++k)
        {
            if (i_ >= s_.size() || s_[i_] != l[k])
                return false;
            ++i_;
        }
        return true;
    }
};

// {x,y} 객체에서 좌표 추출 (누락 시 0)
std::pair<double, double> readXY(const JValue &o)
{
    double x = 0.0, y = 0.0;
    if (const JValue *px = o.find("x"))
        x = px->numOr(0.0);
    if (const JValue *py = o.find("y"))
        y = py->numOr(0.0);
    return {x, y};
}

// ── 읽기 헬퍼 (Message_* → 구조체). 누락 필드는 protobuf 기본값(0/false/"")로 둔다 ──

std::string readStr(const JValue &o, const char *key)
{
    const JValue *v = o.find(key);
    return (v && v->type == JValue::Str) ? v->str : std::string();
}

bool readBool(const JValue &o, const char *key)
{
    const JValue *v = o.find(key);
    return (v && v->type == JValue::Bool) ? v->b : false;
}

double readNum(const JValue &o, const char *key)
{
    const JValue *v = o.find(key);
    return v ? v->numOr(0.0) : 0.0;
}

// Message_MapPos — x/y/z (m)
MapPos readPos(const JValue &o)
{
    MapPos p;
    p.x = readNum(o, "x");
    p.y = readNum(o, "y");
    p.z = readNum(o, "z");
    return p;
}

// Message_MapLine — startPos/endPos
MapLine readLine(const JValue &o)
{
    MapLine l;
    if (const JValue *s = o.find("startPos"))
        l.start_pos = readPos(*s);
    if (const JValue *e = o.find("endPos"))
        l.end_pos = readPos(*e);
    return l;
}

// Message_MapAttribute — description/colorPen/colorBrush/colorFont
MapAttribute readAttribute(const JValue &o)
{
    MapAttribute a;
    if (const JValue *at = o.find("attribute"))
    {
        a.description = readStr(*at, "description");
        a.color_pen = static_cast<std::uint32_t>(readNum(*at, "colorPen"));
        a.color_brush = static_cast<std::uint32_t>(readNum(*at, "colorBrush"));
        a.color_font = static_cast<std::uint32_t>(readNum(*at, "colorFont"));
    }
    return a;
}

// oneof oneof_value 의 JSON 키 ↔ ValueKind 대응표 (proto 92-102줄).
struct OneofEntry
{
    const char *json_key;
    MapProperty::ValueKind kind;
};
const OneofEntry kPropertyOneof[] = {
    {"stringValue", MapProperty::ValueKind::String}, {"boolValue", MapProperty::ValueKind::Bool},
    {"int32Value", MapProperty::ValueKind::Int32},   {"uint32Value", MapProperty::ValueKind::UInt32},
    {"int64Value", MapProperty::ValueKind::Int64},   {"uint64Value", MapProperty::ValueKind::UInt64},
    {"floatValue", MapProperty::ValueKind::Float},   {"doubleValue", MapProperty::ValueKind::Double},
    {"bytesValue", MapProperty::ValueKind::Bytes},
};

// Message_MapProperty 배열. 필드명 `property`(단수)를 쓰는 것이 원본 규약이다.
std::vector<MapProperty> readProperties(const JValue &o, const char *key = "property")
{
    std::vector<MapProperty> out;
    const JValue *arr = o.find(key);
    if (!arr || arr->type != JValue::Arr)
        return out;
    out.reserve(arr->arr.size());
    for (const auto &e : arr->arr)
    {
        MapProperty p;
        p.key = readStr(e, "key");
        p.type = readStr(e, "type");
        p.value = readStr(e, "value");
        p.tag = readStr(e, "tag");
        for (const OneofEntry &oe : kPropertyOneof)
        {
            const JValue *v = e.find(oe.json_key);
            if (!v)
                continue;
            p.kind = oe.kind;
            switch (oe.kind)
            {
            case MapProperty::ValueKind::Bool:
                p.bool_value = (v->type == JValue::Bool) ? v->b : false;
                break;
            case MapProperty::ValueKind::String:
            case MapProperty::ValueKind::Bytes:
            case MapProperty::ValueKind::Int64:
            case MapProperty::ValueKind::UInt64:
                p.str_value = v->str; // proto3 JSON 은 64bit 정수도 문자열로 싣는다
                break;
            default:
                p.num_value = v->numOr(0.0);
                break;
            }
            break; // oneof 이므로 하나만 설정된다
        }
        out.push_back(std::move(p));
    }
    return out;
}

// Message_AdvancedPoint — advancedPointList 원소이자 AdvancedCurve 의 끝점 표현
NamedPoint readAdvancedPoint(const JValue &o)
{
    NamedPoint np;
    np.name = readStr(o, "instanceName");
    np.cls = readStr(o, "className");
    if (const JValue *ps = o.find("pos"))
    {
        const MapPos p = readPos(*ps);
        np.x = p.x;
        np.y = p.y;
        np.z = p.z;
    }
    np.dir = readNum(o, "dir");
    np.ignore_dir = readBool(o, "ignoreDir");
    np.properties = readProperties(o);
    np.attribute = readAttribute(o);
    return np;
}

// 최상위에서 이 로더가 해석하는 키 — 나머지는 unsupported_keys 로 보고한다.
const char *const kKnownTopLevelKeys[] = {
    "mapDirectory",      "header",           "normalPosList",     "normalLineList", "advancedPointList",
    "advancedLineList",  "advancedCurveList", "advancedAreaList", "rssiPosList",    "userData",
};

bool isKnownTopLevelKey(const std::string &k)
{
    for (const char *known : kKnownTopLevelKeys)
        if (k == known)
            return true;
    return false;
}

} // namespace

SmapMap loadSmap(const std::string &path)
{
    SmapMap m;
    std::ifstream f(path, std::ios::binary);
    if (!f)
        return m;
    std::ostringstream ss;
    ss << f.rdbuf();
    const std::string text = ss.str();

    JValue root;
    if (!Parser(text).parse(root) || root.type != JValue::Obj)
        return m;

    m.map_directory = readStr(root, "mapDirectory");
    if (const JValue *h = root.find("header"))
    {
        if (const JValue *r = h->find("resolution"))
            m.resolution = r->numOr(m.resolution);
        if (const JValue *t = h->find("mapType"))
            m.map_type = t->str;
        if (const JValue *n = h->find("mapName"))
            m.map_name = n->str;
        if (const JValue *v = h->find("version"))
            m.version = v->str;
        if (const JValue *mn = h->find("minPos"))
        {
            auto p = readXY(*mn);
            m.min_x = p.first;
            m.min_y = p.second;
        }
        if (const JValue *mx = h->find("maxPos"))
        {
            auto p = readXY(*mx);
            m.max_x = p.first;
            m.max_y = p.second;
        }
    }
    if (const JValue *npl = root.find("normalPosList"))
    {
        m.obstacles.reserve(npl->arr.size());
        for (const auto &e : npl->arr)
            m.obstacles.push_back(readXY(e));
    }
    if (const JValue *rpl = root.find("rssiPosList"))
    {
        for (const auto &e : rpl->arr)
            m.rssi_points.push_back(readXY(e));
    }
    if (const JValue *nll = root.find("normalLineList"))
    {
        m.normal_lines.reserve(nll->arr.size());
        for (const auto &e : nll->arr)
            m.normal_lines.push_back(readLine(e));
    }
    if (const JValue *apl = root.find("advancedPointList"))
    {
        m.named_points.reserve(apl->arr.size());
        for (const auto &e : apl->arr)
            m.named_points.push_back(readAdvancedPoint(e));
    }
    if (const JValue *all = root.find("advancedLineList"))
    {
        m.advanced_lines.reserve(all->arr.size());
        for (const auto &e : all->arr)
        {
            AdvancedLine al;
            al.name = readStr(e, "instanceName");
            al.cls = readStr(e, "className");
            if (const JValue *ln = e.find("line"))
                al.line = readLine(*ln);
            al.properties = readProperties(e);
            al.attribute = readAttribute(e);
            m.advanced_lines.push_back(std::move(al));
        }
    }
    if (const JValue *acl = root.find("advancedCurveList"))
    {
        m.advanced_curves.reserve(acl->arr.size());
        for (const auto &e : acl->arr)
        {
            AdvancedCurve ac;
            ac.name = readStr(e, "instanceName");
            ac.cls = readStr(e, "className");
            if (const JValue *sp = e.find("startPos"))
                ac.start_pos = readAdvancedPoint(*sp);
            if (const JValue *ep = e.find("endPos"))
                ac.end_pos = readAdvancedPoint(*ep);
            if (const JValue *c1 = e.find("controlPos1"))
                ac.control_pos1 = readPos(*c1);
            if (const JValue *c2 = e.find("controlPos2"))
                ac.control_pos2 = readPos(*c2);
            if (const JValue *c3 = e.find("controlPos3"))
                ac.control_pos3 = readPos(*c3);
            if (const JValue *c4 = e.find("controlPos4"))
                ac.control_pos4 = readPos(*c4);
            ac.properties = readProperties(e);
            ac.attribute = readAttribute(e);
            m.advanced_curves.push_back(std::move(ac));
        }
    }
    if (const JValue *aal = root.find("advancedAreaList"))
    {
        m.advanced_areas.reserve(aal->arr.size());
        for (const auto &e : aal->arr)
        {
            AdvancedArea aa;
            aa.name = readStr(e, "instanceName");
            aa.cls = readStr(e, "className");
            if (const JValue *pg = e.find("posGroup"))
            {
                aa.pos_group.reserve(pg->arr.size());
                for (const auto &p : pg->arr)
                    aa.pos_group.push_back(readPos(p));
            }
            aa.dir = readNum(e, "dir");
            aa.properties = readProperties(e);
            aa.attribute = readAttribute(e);
            m.advanced_areas.push_back(std::move(aa));
        }
    }
    m.user_data = readProperties(root, "userData");

    // 해석하지 않은 최상위 키를 기록해 둔다 — saveSmap 이 그만큼 손실 쓰기임을 호출자가 알 수 있다.
    for (const auto &kv : root.obj)
    {
        if (isKnownTopLevelKey(kv.first))
            continue;
        bool dup = false;
        for (const auto &u : m.unsupported_keys)
            dup = dup || (u == kv.first);
        if (!dup)
            m.unsupported_keys.push_back(kv.first);
    }

    m.valid = !m.obstacles.empty();
    return m;
}

namespace
{

// ── 직렬화 (구조체 → protobuf-JSON) ─────────────────────────────────────────
// 규칙: 기본값 필드는 생략, MapProperty 의 oneof 값 필드는 0/false 라도 항상 기록.
// 출력은 원본 Seer 맵과 같은 "공백 없는" 한 줄 JSON 이다.

// double → 다시 읽어도 같은 비트가 나오는 최단 10진 표기.
//   v   : 유한(finite)해야 한다. 호출 전 checkFinite 로 걸러진다.
//   반환: JSON 수치 토큰 (예: -4.38, 0.8272860654453121, 4294901845)
std::string formatNumber(double v)
{
    char buf[48];
    // 15자리면 대부분 그대로 복원되고, 17자리는 IEEE754 배정도 왕복 보장 상한이다.
    const int kMinPrecision = 15, kMaxPrecision = 17;
    for (int prec = kMinPrecision; prec <= kMaxPrecision; ++prec)
    {
        std::snprintf(buf, sizeof(buf), "%.*g", prec, v);
        if (std::strtod(buf, nullptr) == v)
            break;
    }
    return std::string(buf);
}

void writeString(std::string &o, const std::string &s)
{
    o.push_back('"');
    for (const char raw : s)
    {
        const unsigned char c = static_cast<unsigned char>(raw);
        switch (c)
        {
        case '"':
            o += "\\\"";
            break;
        case '\\':
            o += "\\\\";
            break;
        case '\n':
            o += "\\n";
            break;
        case '\r':
            o += "\\r";
            break;
        case '\t':
            o += "\\t";
            break;
        case '\b':
            o += "\\b";
            break;
        case '\f':
            o += "\\f";
            break;
        default:
            if (c < 0x20)
            {
                char esc[8];
                std::snprintf(esc, sizeof(esc), "\\u%04x", c);
                o += esc;
            }
            else
            {
                o.push_back(raw); // UTF-8 바이트는 그대로 통과
            }
        }
    }
    o.push_back('"');
}

// 객체·배열 원소 사이 콤마. 첫 원소면 아무것도 쓰지 않는다.
void sep(std::string &o, bool &first)
{
    if (first)
        first = false;
    else
        o.push_back(',');
}

void writeKey(std::string &o, bool &first, const char *key)
{
    sep(o, first);
    writeString(o, key);
    o.push_back(':');
}

void writeNumField(std::string &o, bool &first, const char *key, double v)
{
    if (v == 0.0)
        return; // 기본값 생략
    writeKey(o, first, key);
    o += formatNumber(v);
}

void writeStrField(std::string &o, bool &first, const char *key, const std::string &v)
{
    if (v.empty())
        return;
    writeKey(o, first, key);
    writeString(o, v);
}

void writeUIntField(std::string &o, bool &first, const char *key, std::uint32_t v)
{
    if (v == 0)
        return;
    writeKey(o, first, key);
    char buf[16];
    std::snprintf(buf, sizeof(buf), "%u", v);
    o += buf;
}

void writeBoolField(std::string &o, bool &first, const char *key, bool v)
{
    if (!v)
        return;
    writeKey(o, first, key);
    o += "true";
}

bool isDefault(const MapPos &p)
{
    return p.x == 0.0 && p.y == 0.0 && p.z == 0.0;
}

bool isDefault(const MapAttribute &a)
{
    return a.description.empty() && a.color_pen == 0 && a.color_brush == 0 && a.color_font == 0;
}

bool isDefault(const MapLine &l)
{
    return isDefault(l.start_pos) && isDefault(l.end_pos);
}

// Message_MapPos 본문 (x=1, y=2, z=3)
void writePosBody(std::string &o, const MapPos &p)
{
    bool first = true;
    o.push_back('{');
    writeNumField(o, first, "x", p.x);
    writeNumField(o, first, "y", p.y);
    writeNumField(o, first, "z", p.z);
    o.push_back('}');
}

// 전 성분 0 이면 필드 자체를 생략한다(원본 규칙).
void writePosField(std::string &o, bool &first, const char *key, const MapPos &p)
{
    if (isDefault(p))
        return;
    writeKey(o, first, key);
    writePosBody(o, p);
}

void writeLineField(std::string &o, bool &first, const char *key, const MapLine &l)
{
    if (isDefault(l))
        return;
    writeKey(o, first, key);
    bool inner = true;
    o.push_back('{');
    writePosField(o, inner, "startPos", l.start_pos);
    writePosField(o, inner, "endPos", l.end_pos);
    o.push_back('}');
}

// Message_MapAttribute (description=1, colorPen=2, colorBrush=3, colorFont=4)
void writeAttributeField(std::string &o, bool &first, const MapAttribute &a)
{
    if (isDefault(a))
        return;
    writeKey(o, first, "attribute");
    bool inner = true;
    o.push_back('{');
    writeStrField(o, inner, "description", a.description);
    writeUIntField(o, inner, "colorPen", a.color_pen);
    writeUIntField(o, inner, "colorBrush", a.color_brush);
    writeUIntField(o, inner, "colorFont", a.color_font);
    o.push_back('}');
}

// Message_MapProperty 배열. oneof 값은 0/false 라도 반드시 기록한다(protobuf-JSON 규칙).
void writePropertiesField(std::string &o, bool &first, const char *key, const std::vector<MapProperty> &props)
{
    if (props.empty())
        return;
    writeKey(o, first, key);
    o.push_back('[');
    bool first_elem = true;
    for (const MapProperty &p : props)
    {
        sep(o, first_elem);
        bool inner = true;
        o.push_back('{');
        writeStrField(o, inner, "key", p.key);
        writeStrField(o, inner, "type", p.type);
        writeStrField(o, inner, "value", p.value);
        switch (p.kind)
        {
        case MapProperty::ValueKind::None:
            break;
        case MapProperty::ValueKind::Bool:
            writeKey(o, inner, "boolValue");
            o += p.bool_value ? "true" : "false";
            break;
        case MapProperty::ValueKind::String:
            writeKey(o, inner, "stringValue");
            writeString(o, p.str_value);
            break;
        case MapProperty::ValueKind::Bytes:
            writeKey(o, inner, "bytesValue");
            writeString(o, p.str_value);
            break;
        case MapProperty::ValueKind::Int64:
            writeKey(o, inner, "int64Value");
            writeString(o, p.str_value);
            break;
        case MapProperty::ValueKind::UInt64:
            writeKey(o, inner, "uint64Value");
            writeString(o, p.str_value);
            break;
        case MapProperty::ValueKind::Int32:
            writeKey(o, inner, "int32Value");
            o += formatNumber(p.num_value);
            break;
        case MapProperty::ValueKind::UInt32:
            writeKey(o, inner, "uint32Value");
            o += formatNumber(p.num_value);
            break;
        case MapProperty::ValueKind::Float:
            writeKey(o, inner, "floatValue");
            o += formatNumber(p.num_value);
            break;
        case MapProperty::ValueKind::Double:
            writeKey(o, inner, "doubleValue");
            o += formatNumber(p.num_value);
            break;
        }
        writeStrField(o, inner, "tag", p.tag);
        o.push_back('}');
    }
    o.push_back(']');
}

// Message_AdvancedPoint 본문
//   (className=1, instanceName=2, pos=3, dir=4, property=5, ignoreDir=6, attribute=10)
void writeAdvancedPointBody(std::string &o, const NamedPoint &p)
{
    bool first = true;
    o.push_back('{');
    writeStrField(o, first, "className", p.cls);
    writeStrField(o, first, "instanceName", p.name);
    writePosField(o, first, "pos", MapPos{p.x, p.y, p.z});
    writeNumField(o, first, "dir", p.dir);
    writePropertiesField(o, first, "property", p.properties);
    writeBoolField(o, first, "ignoreDir", p.ignore_dir);
    writeAttributeField(o, first, p.attribute);
    o.push_back('}');
}

// {x,y} 점 배열 (normalPosList / rssiPosList)
void writeXYListField(std::string &o, bool &first, const char *key,
                      const std::vector<std::pair<double, double>> &pts)
{
    if (pts.empty())
        return;
    writeKey(o, first, key);
    o.push_back('[');
    bool first_elem = true;
    for (const auto &pt : pts)
    {
        sep(o, first_elem);
        writePosBody(o, MapPos{pt.first, pt.second, 0.0});
    }
    o.push_back(']');
}

bool isFinite(double v)
{
    return std::isfinite(v);
}

bool isFinite(const MapPos &p)
{
    return isFinite(p.x) && isFinite(p.y) && isFinite(p.z);
}

bool isFinite(const std::vector<MapProperty> &props)
{
    for (const MapProperty &p : props)
        if (!isFinite(p.num_value))
            return false;
    return true;
}

bool isFinite(const NamedPoint &p)
{
    return isFinite(p.x) && isFinite(p.y) && isFinite(p.z) && isFinite(p.dir) && isFinite(p.properties);
}

// JSON 은 NaN·무한대를 표현할 수 없다 → 쓰기 전에 전수 검사한다(부분 파일 생성 방지).
bool checkFinite(const SmapMap &m)
{
    if (!isFinite(m.resolution) || !isFinite(m.min_x) || !isFinite(m.min_y) || !isFinite(m.max_x) || !isFinite(m.max_y))
        return false;
    for (const auto &pt : m.obstacles)
        if (!isFinite(pt.first) || !isFinite(pt.second))
            return false;
    for (const auto &pt : m.rssi_points)
        if (!isFinite(pt.first) || !isFinite(pt.second))
            return false;
    for (const MapLine &l : m.normal_lines)
        if (!isFinite(l.start_pos) || !isFinite(l.end_pos))
            return false;
    for (const NamedPoint &p : m.named_points)
        if (!isFinite(p))
            return false;
    for (const AdvancedLine &l : m.advanced_lines)
        if (!isFinite(l.line.start_pos) || !isFinite(l.line.end_pos) || !isFinite(l.properties))
            return false;
    for (const AdvancedCurve &c : m.advanced_curves)
    {
        if (!isFinite(c.start_pos) || !isFinite(c.end_pos) || !isFinite(c.properties))
            return false;
        if (!isFinite(c.control_pos1) || !isFinite(c.control_pos2))
            return false;
        if (!isFinite(c.control_pos3) || !isFinite(c.control_pos4))
            return false;
    }
    for (const AdvancedArea &a : m.advanced_areas)
    {
        if (!isFinite(a.dir) || !isFinite(a.properties))
            return false;
        for (const MapPos &p : a.pos_group)
            if (!isFinite(p))
                return false;
    }
    return isFinite(m.user_data);
}

// Message_Map 전체 직렬화. 필드 순서는 proto 의 field number 순(원본 파일과 동일).
std::string serializeSmap(const SmapMap &m)
{
    std::string o;
    // 점 하나당 ~24바이트 + 여유. 재할당 횟수를 줄이기 위한 어림 예약이다.
    const std::size_t kBytesPerPoint = 32;
    o.reserve((m.obstacles.size() + m.rssi_points.size()) * kBytesPerPoint + 1024);

    bool first = true;
    o.push_back('{');
    writeStrField(o, first, "mapDirectory", m.map_directory);

    // Message_MapHeader (mapType=1, mapName=2, minPos=3, maxPos=4, resolution=5, version=8)
    {
        std::string header;
        bool hfirst = true;
        header.push_back('{');
        writeStrField(header, hfirst, "mapType", m.map_type);
        writeStrField(header, hfirst, "mapName", m.map_name);
        writePosField(header, hfirst, "minPos", MapPos{m.min_x, m.min_y, 0.0});
        writePosField(header, hfirst, "maxPos", MapPos{m.max_x, m.max_y, 0.0});
        writeNumField(header, hfirst, "resolution", m.resolution);
        writeStrField(header, hfirst, "version", m.version);
        header.push_back('}');
        if (!hfirst) // 내용이 하나라도 있을 때만 header 를 낸다
        {
            writeKey(o, first, "header");
            o += header;
        }
    }

    writeXYListField(o, first, "normalPosList", m.obstacles);

    if (!m.normal_lines.empty())
    {
        writeKey(o, first, "normalLineList");
        o.push_back('[');
        bool fe = true;
        for (const MapLine &l : m.normal_lines)
        {
            sep(o, fe);
            bool inner = true;
            o.push_back('{');
            writePosField(o, inner, "startPos", l.start_pos);
            writePosField(o, inner, "endPos", l.end_pos);
            o.push_back('}');
        }
        o.push_back(']');
    }

    if (!m.named_points.empty())
    {
        writeKey(o, first, "advancedPointList");
        o.push_back('[');
        bool fe = true;
        for (const NamedPoint &p : m.named_points)
        {
            sep(o, fe);
            writeAdvancedPointBody(o, p);
        }
        o.push_back(']');
    }

    // Message_AdvancedLine (className=1, instanceName=2, line=3, property=4, attribute=10)
    if (!m.advanced_lines.empty())
    {
        writeKey(o, first, "advancedLineList");
        o.push_back('[');
        bool fe = true;
        for (const AdvancedLine &l : m.advanced_lines)
        {
            sep(o, fe);
            bool inner = true;
            o.push_back('{');
            writeStrField(o, inner, "className", l.cls);
            writeStrField(o, inner, "instanceName", l.name);
            writeLineField(o, inner, "line", l.line);
            writePropertiesField(o, inner, "property", l.properties);
            writeAttributeField(o, inner, l.attribute);
            o.push_back('}');
        }
        o.push_back(']');
    }

    // Message_AdvancedCurve (className=1, instanceName=2, startPos=3, endPos=4,
    //                        controlPos1=5, controlPos2=6, property=7, controlPos3=9,
    //                        controlPos4=10, attribute=15)
    if (!m.advanced_curves.empty())
    {
        writeKey(o, first, "advancedCurveList");
        o.push_back('[');
        bool fe = true;
        for (const AdvancedCurve &c : m.advanced_curves)
        {
            sep(o, fe);
            bool inner = true;
            o.push_back('{');
            writeStrField(o, inner, "className", c.cls);
            writeStrField(o, inner, "instanceName", c.name);
            writeKey(o, inner, "startPos");
            writeAdvancedPointBody(o, c.start_pos);
            writeKey(o, inner, "endPos");
            writeAdvancedPointBody(o, c.end_pos);
            writePosField(o, inner, "controlPos1", c.control_pos1);
            writePosField(o, inner, "controlPos2", c.control_pos2);
            writePropertiesField(o, inner, "property", c.properties);
            writePosField(o, inner, "controlPos3", c.control_pos3);
            writePosField(o, inner, "controlPos4", c.control_pos4);
            writeAttributeField(o, inner, c.attribute);
            o.push_back('}');
        }
        o.push_back(']');
    }

    // Message_AdvancedArea (className=1, instanceName=2, posGroup=3, dir=4, property=5, attribute=15)
    if (!m.advanced_areas.empty())
    {
        writeKey(o, first, "advancedAreaList");
        o.push_back('[');
        bool fe = true;
        for (const AdvancedArea &a : m.advanced_areas)
        {
            sep(o, fe);
            bool inner = true;
            o.push_back('{');
            writeStrField(o, inner, "className", a.cls);
            writeStrField(o, inner, "instanceName", a.name);
            if (!a.pos_group.empty())
            {
                writeKey(o, inner, "posGroup");
                o.push_back('[');
                bool fp = true;
                for (const MapPos &p : a.pos_group)
                {
                    sep(o, fp);
                    writePosBody(o, p);
                }
                o.push_back(']');
            }
            writeNumField(o, inner, "dir", a.dir);
            writePropertiesField(o, inner, "property", a.properties);
            writeAttributeField(o, inner, a.attribute);
            o.push_back('}');
        }
        o.push_back(']');
    }

    writeXYListField(o, first, "rssiPosList", m.rssi_points);
    writePropertiesField(o, first, "userData", m.user_data);

    o.push_back('}');
    return o;
}

} // namespace

bool saveSmap(const SmapMap &m, const std::string &path)
{
    if (!checkFinite(m))
        return false;
    const std::string text = serializeSmap(m);
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    if (!f)
        return false;
    f.write(text.data(), static_cast<std::streamsize>(text.size()));
    f.flush();
    return static_cast<bool>(f);
}

} // namespace mcl2d
