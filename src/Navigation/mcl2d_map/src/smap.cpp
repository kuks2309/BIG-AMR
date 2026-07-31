#include "mcl2d_map/smap.hpp"

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

    if (const JValue *h = root.find("header"))
    {
        if (const JValue *r = h->find("resolution"))
            m.resolution = r->numOr(m.resolution);
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
    if (const JValue *apl = root.find("advancedPointList"))
    {
        for (const auto &e : apl->arr)
        {
            NamedPoint np;
            if (const JValue *nm = e.find("instanceName"))
                np.name = nm->str;
            if (const JValue *cl = e.find("className"))
                np.cls = cl->str;
            if (const JValue *ps = e.find("pos"))
            {
                auto p = readXY(*ps);
                np.x = p.first;
                np.y = p.second;
            }
            if (const JValue *dr = e.find("dir"))
                np.dir = dr->numOr(0.0);
            m.named_points.push_back(std::move(np));
        }
    }
    m.valid = !m.obstacles.empty();
    return m;
}

} // namespace mcl2d
