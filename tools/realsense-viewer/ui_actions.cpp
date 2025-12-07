#include "ui_actions.h"
#include "ui_dump.h"
#include <imgui.h>
#include <imgui_internal.h>
#include <atomic>
#include <mutex>
#include <unordered_map>
#include <vector>
#include <cstring>
#include <netinet/in.h>
#include <unistd.h>
#include <cerrno>

// helpers for robust input parsing
static bool parse_double(const std::string& s, double& out){
    if(s.empty()) return false;
    char* end=nullptr; errno=0;
    out = strtod(s.c_str(), &end);
    return end && *end=='\0' && errno==0;
}
static bool parse_ull(const std::string& s, unsigned long long& out){
    if(s.empty()) return false;
    char* end=nullptr; errno=0;
    unsigned long long v = strtoull(s.c_str(), &end, 10);
    if(!(end && *end=='\0' && errno==0)) return false;
    out = v; return true;
}

static std::thread g_srv;
static std::atomic<bool> g_run{false};

// simple queue to bridge from server thread to render thread
struct Cmd {
    enum Type{Click, Scroll, TypeTxt, ScrollReveal} type;
    float x=0,y=0,dx=0,dy=0;
    uint64_t id=0;
    std::string text;
};
static std::mutex g_mtx;
static std::vector<Cmd> g_queue;

void ui_click(float x, float y){
    ImGuiIO& io = ImGui::GetIO();
    io.AddMousePosEvent(x,y);
    io.AddMouseButtonEvent(0,true);
    io.AddMouseButtonEvent(0,false);
}
bool ui_scroll(uint64_t container_id, float dx, float dy){
    // locate the container in current frame dump and adjust scroll
    auto it = g_uidump.cur.containers.find(container_id);
    if(it==g_uidump.cur.containers.end()) return false;
    // we can't write into ImGuiWindow scroll here; do it from the render thread:
    return true;
}
void ui_type_utf8(const std::string& s){
    ImGuiIO& io = ImGui::GetIO();
    io.AddInputCharactersUTF8(s.c_str());
}
bool ui_scroll_to_reveal(uint64_t item_id){
    // plan: find item, find its container, compute delta and push a Scroll command
    for(auto& n : g_uidump.cur.nodes){
        if(n.id==item_id && n.container_id){
            auto it = g_uidump.cur.containers.find(n.container_id);
            if(it==g_uidump.cur.containers.end()) return false;
            auto si = it->second;
            // compute minimal dy to bring item bbox into container visible rect
            float top = n.min.y, bot = n.max.y;
            // assume container visible rect [0..size.y] in window space; ImGui keeps coords in screen space,
            // but for a simple heuristic use pixel deltas:
            float dy=0;
            if(top < 0) dy = top - 8; else if(bot > si.size.y) dy = bot - si.size.y + 8;
            if(dy!=0){
                std::lock_guard<std::mutex> lk(g_mtx);
                g_queue.push_back(Cmd{Cmd::Scroll,0,0,0,dy,n.container_id,{}});
                return true;
            }
            return true; // already visible
        }
    }
    return false;
}

// called from render thread once per frame
static void pump_commands_from_queue(){
    std::vector<Cmd> local;
    { std::lock_guard<std::mutex> lk(g_mtx); local.swap(g_queue); }
    for(auto& c: local){
        if(c.type==Cmd::Click) ui_click(c.x,c.y);
        else if(c.type==Cmd::TypeTxt) ui_type_utf8(c.text);
        else if(c.type==Cmd::Scroll){
            // find window by container id and mutate its Scroll
            ImGuiContext* ctx = ImGui::GetCurrentContext();
            if(!ctx) continue;
            for(ImGuiWindow* w : ctx->Windows){
                if((uint64_t)w->ID == c.id){
                    // Manual clamp implementation since std::clamp requires C++17
                    float new_y = w->Scroll.y + c.dy;
                    w->Scroll.y = (new_y < 0.0f) ? 0.0f : ((new_y > w->ScrollMax.y) ? w->ScrollMax.y : new_y);
                    float new_x = w->Scroll.x + c.dx;
                    w->Scroll.x = (new_x < 0.0f) ? 0.0f : ((new_x > w->ScrollMax.x) ? w->ScrollMax.x : new_x);
                }
            }
        } else if(c.type==Cmd::ScrollReveal){ ui_scroll_to_reveal(c.id); }
    }
}

// very tiny blocking TCP server (single connection at a time)
static void serve(unsigned short port){
    int s = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in addr{}; addr.sin_family=AF_INET; addr.sin_port=htons(port); addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    int yes=1; setsockopt(s,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
    bind(s,(sockaddr*)&addr,sizeof(addr));
    listen(s,1);
    while(g_run){
        int c = accept(s,nullptr,nullptr);
        if(c<0) continue;
        char buf[2048]; int n = read(c, buf, sizeof(buf)-1); if(n<=0){ close(c); continue; }
        buf[n]=0;
        std::string req(buf, n);
        auto ok=[&](const char* msg){ std::string r="HTTP/1.1 200 OK\r\nContent-Length: "; r+=std::to_string(strlen(msg));
            r+="\r\n\r\n"; r+=msg; write(c,r.data(),r.size()); };
        auto bad=[&](const char* msg){ std::string r="HTTP/1.1 400 Bad\r\nContent-Length: "; r+=std::to_string(strlen(msg));
            r+="\r\n\r\n"; r+=msg; write(c,r.data(),r.size()); };

        auto qpos = req.find(' ');
        auto qend = req.find(' ', qpos+1);
        std::string line = req.substr(qpos+1, qend-qpos-1); // e.g. /click?x=100&y=200
        auto path = line;
        auto qm = line.find('?');
        std::string query;
        if(qm!=std::string::npos){ path=line.substr(0,qm); query=line.substr(qm+1); }
        auto get = [&](const char* key)->std::string{
            auto k = std::string(key) + "=";
            auto p = query.find(k); if(p==std::string::npos) return {};
            auto e = query.find('&', p+k.size());
            return query.substr(p+k.size(), e==std::string::npos?std::string::npos:e-(p+k.size()));
        };

        if(path=="/click"){
            double x,y; if(!parse_double(get("x"),x) || !parse_double(get("y"),y)){ bad("bad x/y"); }
            else { std::lock_guard<std::mutex> lk(g_mtx); g_queue.push_back(Cmd{Cmd::Click,(float)x,(float)y}); ok("clicked"); }
        } else if(path=="/scroll"){
            unsigned long long id; double dx,dy;
            if(!parse_ull(get("id"),id) || !parse_double(get("dx"),dx) || !parse_double(get("dy"),dy)){ bad("bad id/dx/dy"); }
            else { std::lock_guard<std::mutex> lk(g_mtx); g_queue.push_back(Cmd{Cmd::Scroll,0,0,(float)dx,(float)dy,(uint64_t)id,{}}); ok("scrolled"); }
        } else if(path=="/type"){
            // body after blank line
            auto p = req.find("\r\n\r\n"); std::string body = (p==std::string::npos)?"":req.substr(p+4);
            std::lock_guard<std::mutex> lk(g_mtx);
            g_queue.push_back(Cmd{Cmd::TypeTxt,0,0,0,0,0,body});
            ok("typed");
        } else if(path=="/scroll_to_reveal"){
            unsigned long long id;
            if(!parse_ull(get("id"),id)){ bad("bad id"); }
            else { std::lock_guard<std::mutex> lk(g_mtx); g_queue.push_back(Cmd{Cmd::ScrollReveal,0,0,0,0,(uint64_t)id,{}}); ok("revealing"); }
        } else {
            bad("unknown");
        }
        close(c);
    }
    close(s);
}

void ui_actions_start(unsigned short port){
    if(g_run.exchange(true)) return;
    g_srv = std::thread([=]{ serve(port); });
}
void ui_actions_stop(){
    if(!g_run.exchange(false)) return;
    // connect to self to unblock accept()
    int s = ::socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in a{}; a.sin_family=AF_INET; a.sin_port=htons(8787); a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    connect(s,(sockaddr*)&a,sizeof(a)); close(s);
    if(g_srv.joinable()) g_srv.join();
}

// call from render thread each frame
void ui_actions_frame_tick(){
    pump_commands_from_queue();
}
