import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from contextlib import asynccontextmanager
import subprocess
import os
import signal
import json
import sys

# === 默认配置 ===
DEFAULT_CONFIG = {
    "ENABLE_PROXY": False,
    "PROXY_URL": "socks5://192.168.2.1:7891",
    "API_ID": 0, "API_HASH": "", "STRING_SESSION": "",
    "ENABLE_NOTIFY": False, "BOT_TOKEN": "", "BOT_CHAT_ID": "", "NOTIFY_KEYWORDS": ["怪奇物语", "失序边缘"],
    "ALIST_URL": "http://192.168.2.1:4567/api/shares/", "ALIST_KEY": "",
    "MONITOR_INTERVAL_HOURS": 3,
    "MONITOR_LIMIT": 3000, "MONITOR_DAYS": 365, "SMART_STOP_COUNT": 50,
    "CONCURRENT_LIMITS": {"a189": 10, "baidu": 1, "uc": 5, "a123": 5, "default": 5},
    "ENABLE_189": True, "ENABLE_BAIDU": True, "ENABLE_UC": True, "ENABLE_123": True,
    "CHANNEL_URLS": ["https://t.me/tyysypzypd", "https://t.me/tianyirigeng", "https://t.me/cloudtianyi"],
    "EXCLUDE_KEYWORDS": ["小程序", "预告", "电子书", "破解版", "安卓", "课程", "PDF", "有声书", "网赚", "音乐", "写真", "抖音", "短剧", "综艺", "真人秀"],
    "API_CONFIGS": [
        {"name": "TV Show", "folder_prefix": "剧集/", "priority_keywords": ["权力的游戏"], "required_keywords": [], "optional_keywords": ["季", "集", "EP", "S0", "剧集"], "excluded_keywords": ["低码", "普码"]},
        {"name": "Movies", "folder_prefix": "电影/", "priority_keywords": [], "required_keywords": [], "optional_keywords": ["原盘", "REMUX", "4K", "HDR", "电影"], "excluded_keywords": ["枪版", "TC"]}
    ]
}

CONFIG_FILE = "/app/data/config.json"
LOG_FILE = "/app/data/app.log"
PROCESS = None

APP_VERSION = os.getenv("APP_VERSION", "v2.8.1 Pro")
AVATAR_URL = "https://i.imgs.ovh/2025/12/11/Cn5Jhq.jpeg"
PERSONAL_SITE_URL = "https://your-personal-website.com" 

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def run_worker():
    global PROCESS
    if PROCESS:
        try: os.kill(PROCESS.pid, signal.SIGTERM)
        except: pass
    if not os.path.exists(LOG_FILE): open(LOG_FILE, 'w').close()
    log_fd = open(LOG_FILE, "a", encoding='utf-8')
    PROCESS = subprocess.Popen([sys.executable, "-u", "core.py"], stdout=log_fd, stderr=log_fd, cwd="/app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists("/app/data"): os.makedirs("/app/data")
    load_config()
    run_worker()
    yield
    if PROCESS:
        try: os.kill(PROCESS.pid, signal.SIGTERM)
        except: pass

app = FastAPI(lifespan=lifespan)

HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AT-Spider丨管理面板</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🕷️</text></svg>">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/vue@2.6.14/dist/vue.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        body {{ background: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; padding-top: 70px; }}
        
        .navbar-custom {{
            background-color: #ffffff;
            box-shadow: 0 2px 15px rgba(0,0,0,0.04);
            border-bottom: 1px solid #f0f0f0;
            padding: 12px 0;
        }}
        .navbar-brand {{
            font-weight: 700;
            font-size: 1.35rem;
            color: #333 !important;
            display: flex; align-items: center; gap: 10px;
        }}
        .logo-spider {{
            width: 32px; height: 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 20px;
            box-shadow: 0 4px 6px rgba(118, 75, 162, 0.3);
        }}
        .nav-link {{ color: #555 !important; font-weight: 500; margin-left: 15px; transition: color 0.2s; }}
        .nav-link:hover {{ color: #0d6efd !important; }}
        .nav-link.active {{ color: #0d6efd !important; font-weight: 600; }}

        .main-container {{ max-width: 1400px; margin: 20px auto 0; padding: 0 15px; min-height: calc(100vh - 450px); }}
        
        /* 🌟 新增：滚动公告栏样式 */
        .notice-bar {{
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            margin: 20px auto 0;
            max-width: 1400px; /* 与下方容器宽度一致 */
            padding: 12px 20px;
            display: flex;
            align-items: center;
            border: 1px solid #eef2f5;
        }}
        .notice-icon {{
            font-size: 1.2rem;
            margin-right: 15px;
            color: #555;
        }}
        .notice-content {{
            flex: 1;
            overflow: hidden;
            white-space: nowrap;
            font-size: 14px;
            color: #333;
            font-weight: 500;
        }}
        /* 使用 CSS 动画实现平滑滚动 */
        .marquee {{
            display: inline-block;
            padding-left: 100%;
            animation: marquee 20s linear infinite;
        }}
        @keyframes marquee {{
            0% {{ transform: translate(0, 0); }}
            100% {{ transform: translate(-100%, 0); }}
        }}
        .notice-arrow {{
            margin-left: 15px;
            color: #aaa;
            cursor: pointer;
        }}

        .card {{ border: none; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); transition: transform 0.2s; margin-bottom: 20px; }}
        .card-header {{ background: #fff; border-bottom: 1px solid #f0f0f0; border-radius: 12px 12px 0 0 !important; padding: 15px 20px; font-weight: 600; }}
        
        .log-box {{ 
            background: #fdfdfd; color: #344767; height: 500px; overflow-y: scroll; padding: 20px; 
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; 
            font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; 
            border-radius: 0 0 12px 12px; border-top: 1px solid #f0f0f0; box-shadow: inset 0 2px 6px rgba(0,0,0,0.015);
        }}
        .log-box::-webkit-scrollbar {{ width: 8px; }}
        .log-box::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        .log-box::-webkit-scrollbar-thumb {{ background: #ccc; border-radius: 4px; }}
        .log-box::-webkit-scrollbar-thumb:hover {{ background: #bbb; }}

        .log-btn-group .btn {{ border-radius: 6px; margin-left: 5px; font-size: 0.85rem; }}

        .nav-tabs {{ border-bottom: 2px solid #eee; }}
        .nav-tabs .nav-link {{ border: none; color: #666; font-weight: 500; padding: 10px 20px; transition: all 0.3s; }}
        .nav-tabs .nav-link.active {{ color: #0d6efd; background: transparent; border-bottom: 2px solid #0d6efd; }}
        .nav-tabs .nav-link:hover {{ color: #0d6efd; }}

        .site-footer {{ background: #fff; padding: 30px 0 20px; margin-top: 20px; border-top: 1px solid #eaeaea; color: #666; }}
        .social-icons {{ display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 25px; }}
        .social-icon {{ width: 36px; height: 36px; background: #333; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; transition: all 0.3s ease; }}
        .social-icon:hover {{ transform: translateY(-3px); background: #000; }}
        .social-icon svg {{ width: 18px; height: 18px; fill: currentColor; }}
        
        .avatar-icon {{ 
            width: 64px; height: 64px; border-radius: 50%; overflow: hidden; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.25); border: 3px solid #fff; 
            transition: transform 0.3s; display: block; 
        }}
        .avatar-icon:hover {{ transform: scale(1.1); box-shadow: 0 6px 20px rgba(0,0,0,0.3); }}
        .avatar-icon img {{ width: 100%; height: 100%; object-fit: cover; }}
        
        .footer-columns {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 20px; max-width: 1000px; margin: 0 auto 25px; text-align: left; padding: 0 20px; }}
        .footer-col h5 {{ font-size: 15px; font-weight: 700; color: #333; margin-bottom: 15px; }}
        .footer-col ul {{ list-style: none; padding: 0; margin: 0; }}
        .footer-col li {{ margin-bottom: 8px; }}
        .footer-col a {{ color: #666; text-decoration: none; font-size: 13px; transition: color 0.2s; }}
        .footer-col a:hover {{ color: #0d6efd; }}

        .footer-copyright {{ padding-top: 10px; text-align: center; font-size: 14px; color: #555; }}
        .footer-copyright p {{ margin: 5px 0; }}
        .footer-copyright strong {{ font-weight: 700; color: #222; }}
        .footer-copyright a {{ color: #555; text-decoration: none; font-weight: 600; transition: color 0.2s; }}
        .footer-copyright a:hover {{ color: #0d6efd; }}
        .footer-copyright .badge {{ font-size: 11px; padding: 3px 6px; border-radius: 4px; background: #6c757d; color: #fff; font-weight: normal; vertical-align: text-bottom; }}
        .separator {{ margin: 0 5px; color: #ccc; }}
    </style>
</head>
<body>

<div id="app">
    <nav class="navbar navbar-expand-lg navbar-custom fixed-top">
        <div class="container-fluid" style="max-width: 1430px;">
            <a class="navbar-brand" href="#">
                <div class="logo-spider">🕷️</div>
                <span>AT-Spider</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item"><a class="nav-link active" href="https://hub.docker.com/r/xudahua520/AT-Spider">🐳 Docker</a></li>
                    <li class="nav-item"><a class="nav-link" href="https://github.com/xudahua520/AT-Spider" target="_blank">🐱 Github</a></li>
                    <li class="nav-item"><a class="nav-link" href="#" onclick="alert('AT-Spider Bot\\n版本: {APP_VERSION}\\n作者: Deva');return false;">ℹ️ 关于</a></li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- 🌟 新增：滚动通知栏 -->
    <div class="container-fluid" style="max-width: 1430px; padding: 0 15px;">
        <div class="notice-bar">
            <div class="notice-icon">📢</div>
            <div class="notice-content">
                <div class="marquee">
                    欢迎使用 AT-Spider！本系统支持自动化监控 Telegram 频道并转存资源至 Alist-Tvbox。如有问题请提交 Issue，祝您使用愉快！ ( 感谢Alist-Tvbox电报官方群组的 我就问这瓜保熟不 & tcxp 提供的py脚本 )
                </div>
            </div>
            <div class="notice-arrow">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
            </div>
        </div>
    </div>

    <div class="main-container">
        <div class="row">
            <!-- 左侧配置 -->
            <div class="col-lg-7">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>⚙️ 参数配置中心</span>
                        <button class="btn btn-primary btn-sm px-3" @click="saveConfig" :disabled="loading">
                            {{{{ loading ? '应用中...' : '💾 保存并重启' }}}}
                        </button>
                    </div>
                    <div class="card-body">
                        <ul class="nav nav-tabs mb-4">
                            <li class="nav-item"><a class="nav-link" :class="{{active: tab=='basic'}}" @click="tab='basic'" href="#">基础设置</a></li>
                            <li class="nav-item"><a class="nav-link" :class="{{active: tab=='scan'}}" @click="tab='scan'" href="#">扫描与通知</a></li>
                            <li class="nav-item"><a class="nav-link" :class="{{active: tab=='rules'}}" @click="tab='rules'" href="#">规则与频道</a></li>
                        </ul>

                        <div v-if="tab=='basic'">
                            <div class="row">
                                <div class="col-md-4 mb-3"><label class="form-label">API ID</label><input type="number" class="form-control" v-model.number="c.API_ID"></div>
                                <div class="col-md-8 mb-3"><label class="form-label">API Hash</label><input type="text" class="form-control" v-model="c.API_HASH"></div>
                                <div class="col-12 mb-3">
                                    <label class="form-label text-primary fw-bold">Telegram Session String (必填)</label>
                                    <input type="text" class="form-control" v-model="c.STRING_SESSION" style="font-family:monospace;font-size:12px;">
                                </div>
                            </div>
                            <hr class="my-4">
                            <div class="row">
                                <div class="col-md-6 mb-3"><label class="form-label">Alist URL</label><input type="text" class="form-control" v-model="c.ALIST_URL"></div>
                                <div class="col-md-6 mb-3"><label class="form-label">Alist Token</label><input type="password" class="form-control" v-model="c.ALIST_KEY"></div>
                            </div>
                            <div class="bg-light p-3 rounded">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" v-model="c.ENABLE_PROXY">
                                    <label class="form-check-label fw-bold">启用网络代理</label>
                                </div>
                                <div class="mt-2" v-if="c.ENABLE_PROXY">
                                    <input type="text" class="form-control" v-model="c.PROXY_URL" placeholder="socks5://192.168.1.5:7891">
                                    <small class="text-muted d-block mt-1">Host模式填 127.0.0.1，Bridge模式填宿主机IP</small>
                                </div>
                            </div>
                        </div>

                        <div v-if="tab=='scan'">
                            <div class="row">
                                <div class="col-md-4 mb-3"><label class="form-label">扫描间隔 (小时)</label><input type="number" class="form-control" v-model.number="c.MONITOR_INTERVAL_HOURS"></div>
                                <div class="col-md-4 mb-3"><label class="form-label">单次限制 (条)</label><input type="number" class="form-control" v-model.number="c.MONITOR_LIMIT"></div>
                                <div class="col-md-4 mb-3"><label class="form-label">智能中断 (条)</label><input type="number" class="form-control" v-model.number="c.SMART_STOP_COUNT"></div>
                            </div>
                            <hr>
                            <label class="form-label fw-bold mb-2">网盘开关</label>
                            <div class="d-flex gap-3 mb-3">
                                <div class="form-check"><input class="form-check-input" type="checkbox" v-model="c.ENABLE_189"><label>天翼</label></div>
                                <div class="form-check"><input class="form-check-input" type="checkbox" v-model="c.ENABLE_BAIDU"><label>百度</label></div>
                                <div class="form-check"><input class="form-check-input" type="checkbox" v-model="c.ENABLE_UC"><label>UC</label></div>
                                <div class="form-check"><input class="form-check-input" type="checkbox" v-model="c.ENABLE_123"><label>123</label></div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">并发控制 (JSON)</label>
                                <textarea class="form-control font-monospace" rows="2" v-model="concurrentStr" style="font-size:12px"></textarea>
                            </div>
                            <div class="bg-light p-3 rounded">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" v-model="c.ENABLE_NOTIFY">
                                    <label class="form-check-label fw-bold">Telegram 机器人通知</label>
                                </div>
                                <div class="row mt-2" v-if="c.ENABLE_NOTIFY">
                                    <div class="col-md-6 mb-2"><input type="text" class="form-control form-control-sm" placeholder="Bot Token" v-model="c.BOT_TOKEN"></div>
                                    <div class="col-md-6 mb-2"><input type="text" class="form-control form-control-sm" placeholder="Chat ID" v-model="c.BOT_CHAT_ID"></div>
                                    <div class="col-12"><input type="text" class="form-control form-control-sm" placeholder="关键词(逗号隔开)" v-model="notifyKwStr"></div>
                                </div>
                            </div>
                        </div>

                        <div v-if="tab=='rules'">
                            <div class="mb-3">
                                <label class="form-label">监控频道列表</label>
                                <textarea class="form-control font-monospace" rows="5" v-model="channelsStr" style="font-size:12px"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">分类识别规则</label>
                                <textarea class="form-control font-monospace" rows="8" v-model="apiConfigStr" style="font-size:12px"></textarea>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">关键词过滤</label>
                                <textarea class="form-control font-monospace" rows="4" v-model="excludeStr" style="font-size:12px"></textarea>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧日志 -->
            <div class="col-lg-5">
                <div class="card h-100">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span>📊 运行日志</span>
                        <div class="log-btn-group">
                            <a href="/api/download_log" target="_blank" class="btn btn-outline-info btn-sm">📥 导出</a>
                            <button class="btn btn-outline-secondary btn-sm" @click="fetchLogs">刷新</button>
                            <button class="btn btn-sm" :class="autoRefresh ? 'btn-success':'btn-secondary'" @click="autoRefresh=!autoRefresh">
                                {{{{ autoRefresh ? '自动: 开' : '自动: 关' }}}}
                            </button>
                        </div>
                    </div>
                    <div class="card-body p-0">
                        <div class="log-box" id="logBox">{{{{ logs }}}}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer class="site-footer">
        <div class="social-icons">
            <a href="https://github.com/xudahua520/AT-Spider" target="_blank" class="social-icon" title="Github"><svg viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg></a>
            <a href="mailto:xudahua520@gmail.com" class="social-icon" title="Email"><svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg></a>
            <a href="{PERSONAL_SITE_URL}" target="_blank" class="avatar-icon"><img src="{AVATAR_URL}" alt="Admin"></a>
            <a href="https://t.me/Deva520" target="_blank" class="social-icon" title="Telegram"><svg viewBox="0 0 24 24"><path d="M20.665 3.717l-17.73 6.837c-1.21.486-1.203 1.161-.222 1.462l4.552 1.42 10.532-6.645c.498-.303.953-.14.579.192l-8.533 7.701h-.002l.002.001-.314 4.692c.46 0 .663-.211.921-.46l2.211-2.15 4.599 3.397c.848.467 1.457.227 1.668-.785l3.019-14.228c.309-1.239-.473-1.8-1.282-1.434z"/></svg></a>
            <a href="tencent://message/?uin=95317341" class="social-icon" title="QQ"><svg viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12c0 6.627 5.373 12 12 12s12-5.373 12-12C24 5.373 18.627 0 12 0zm0 3c1.77 0 3.32.72 4.47 1.88C17.62 6.03 18 7.37 18 9c0 1.63-.38 2.97-1.53 4.12C15.32 14.28 13.77 15 12 15s-3.32-.72-4.47-1.88C6.38 11.97 6 10.63 6 9c0-1.63.38-2.97 1.53-4.12C8.68 3.72 10.23 3 12 3zm0 13c-2.67 0-5.18-.87-7.23-2.34C3.65 15.6 3 18.23 3 19c0 .55.45 1 1 1h16c.55 0 1-.45 1-1 0-.77-.65-3.4-1.77-5.34C17.18 15.13 14.67 16 12 16z"/></svg></a>
        </div>        
        <div class="footer-copyright">
            <p>
                © 2024 - 2025 By Deva <span class="separator">|</span> <span class="badge">{APP_VERSION}</span>
            </p>
            <p>
                项目: <a href="https://github.com/xudahua520/AT-Spider" target="_blank">AT-Spider</a> &nbsp;
                Powered by: 我就问这瓜保熟不 & tcxp
            </p>
        </div>
    </footer>
</div>

<script>
new Vue({{
    el: '#app',
    data: {{ tab: 'basic', loading: false, c: {{}}, concurrentStr: '', channelsStr: '', notifyKwStr: '', apiConfigStr: '', excludeStr: '', logs: 'Loading logs...', autoRefresh: true }},
    mounted() {{ this.loadConfig(); setInterval(() => {{ if(this.autoRefresh) this.fetchLogs() }}, 3000); }},
    methods: {{
        loadConfig() {{
            axios.get('/api/config').then(res => {{
                this.c = res.data;
                this.concurrentStr = JSON.stringify(this.c.CONCURRENT_LIMITS || {{}}, null, 4);
                this.channelsStr = JSON.stringify(this.c.CHANNEL_URLS || [], null, 4);
                this.apiConfigStr = JSON.stringify(this.c.API_CONFIGS || [], null, 4);
                this.excludeStr = JSON.stringify(this.c.EXCLUDE_KEYWORDS || [], null, 4);
                this.notifyKwStr = (this.c.NOTIFY_KEYWORDS || []).join(', ');
            }});
        }},
        saveConfig() {{
            try {{
                this.c.CONCURRENT_LIMITS = JSON.parse(this.concurrentStr);
                this.c.CHANNEL_URLS = JSON.parse(this.channelsStr);
                this.c.API_CONFIGS = JSON.parse(this.apiConfigStr);
                this.c.EXCLUDE_KEYWORDS = JSON.parse(this.excludeStr);
                this.c.NOTIFY_KEYWORDS = this.notifyKwStr.split(/[,，]/).map(s => s.trim()).filter(s => s);
                this.loading = true;
                axios.post('/api/config', this.c).then(res => {{
                    alert('保存成功，后台进程已重启'); this.loading = false; this.fetchLogs();
                }}).catch(e => {{ alert('保存失败: '+e); this.loading = false; }});
            }} catch (e) {{ alert('JSON 格式错误，请检查输入！\\n' + e); this.loading = false; }}
        }},
        fetchLogs() {{
            axios.get('/api/logs').then(res => {{
                this.logs = res.data.logs;
                const box = document.getElementById('logBox');
                if(box) box.scrollTop = box.scrollHeight;
            }});
        }}
    }}
}})
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index(): return HTML_TEMPLATE

@app.get("/api/download_log")
async def download_log():
    if os.path.exists(LOG_FILE): return FileResponse(LOG_FILE, media_type='text/plain', filename='app.log')
    return {"error": "Log file not found"}

@app.get("/api/config")
async def get_config(): return load_config()

@app.post("/api/config")
async def save_config(config: dict):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4, ensure_ascii=False)
    run_worker()
    return {"status": "ok"}

@app.get("/api/logs")
async def get_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return {"logs": "".join(lines[-200:])}
    return {"logs": "No logs yet..."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8877, access_log=False)