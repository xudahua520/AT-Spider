import asyncio
import re
import os
import sqlite3
import aiohttp
import sys
import traceback
import time
import logging
import bisect
import json
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

# Telegram 库
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl, KeyboardButtonUrl
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import ResolveUsernameRequest

# ==============================================================================
# ====== 🛠️ 配置加载区域 =========================================================
# ==============================================================================

CONFIG_PATH = "/app/data/config.json"

def get_cfg():
    if not os.path.exists(CONFIG_PATH): return {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

cfg = get_cfg()

# --- 1. 基础配置 ---
ENABLE_PROXY = cfg.get("ENABLE_PROXY", False)
PROXY_URL = cfg.get("PROXY_URL", "")
API_ID = cfg.get("API_ID", 0)
API_HASH = cfg.get("API_HASH", "")
STRING_SESSION = cfg.get("STRING_SESSION", "")

NOTIFY_KEYWORDS = cfg.get("NOTIFY_KEYWORDS", [])
ENABLE_NOTIFY = cfg.get("ENABLE_NOTIFY", False)
BOT_TOKEN = cfg.get("BOT_TOKEN", "")
BOT_CHAT_ID = cfg.get("BOT_CHAT_ID", "")

ALIST_URL = cfg.get("ALIST_URL", "")
ALIST_KEY = cfg.get("ALIST_KEY", "")

SAVE_PATH = "/app/data"
LOOP_SWITCH = 1 # Docker模式强制循环
MONITOR_INTERVAL_HOURS = cfg.get("MONITOR_INTERVAL_HOURS", 3)

MONITOR_LIMIT = cfg.get("MONITOR_LIMIT", 3000)
MONITOR_DAYS = cfg.get("MONITOR_DAYS", 365)
SMART_STOP_COUNT = cfg.get("SMART_STOP_COUNT", 50)
DB_RETENTION_DAYS = 30

CONCURRENT_LIMITS = cfg.get("CONCURRENT_LIMITS", {"default": 5})

ENABLE_189 = cfg.get("ENABLE_189", True)
ENABLE_BAIDU = cfg.get("ENABLE_BAIDU", True)
ENABLE_UC = cfg.get("ENABLE_UC", True)
ENABLE_123 = cfg.get("ENABLE_123", True)

CHANNEL_URLS = cfg.get("CHANNEL_URLS", [])
EXCLUDE_KEYWORDS = cfg.get("EXCLUDE_KEYWORDS", [])
API_CONFIGS = cfg.get("API_CONFIGS", [])

# --- 固定的正则与清洗规则 ---
JUNK_LINE_KEYWORDS = ["福利", "频道", "关注", "置顶", "推荐", "via", "转自", "来源", "投稿", "小编", "整理", "失效", "补档", "禁言", "通知", "更新", "日更", "公众号", "加入", "点击", "领取", "打开百度", "保存到", "手机", "电脑"]
COMMON_AD_REGEX = [r'天翼云盘.*资源分享', r'via\s*🤖編號\s*9527', r'🏷?\s*标签\s*：.*', r'[🏷#]\s*\w+', r'UC网盘.*分享', r'资源编号：\d+', r'123网盘.*分享', r'https?://\S+', r'[a-zA-Z0-9]+\.(cn|com|net)/\S+', r'百度网盘.*分享']
TECH_REMOVE_KEYWORDS = ["低码率", "低码", "高码率", "高码", "普码", "杜比视界", "杜比", "视界", "臻彩", "超清", "高清", "蓝光", "原盘"]
TECH_REMOVE_REGEX = [r'\b60\s*(FPS|fps|帧)\b', r'60\s*帧', r'\b(4K|2160[Pp]?|1080[Pp]?|720[Pp]?|480[Pp]?|8K)\b', r'\b(HDR\d*|SDR|DV|Dolby\s*Vision|DoVi|HLG)\b', r'\b(HEVC|x265|H\.?265|x264|H\.?264|AVC|REMUX|ISO|BD|BluRay|WEB-DL|WEBRip|HDTV)\b', r'\b(HQ|HD|UHD|FHD)\b', r'\b(Atmos|DDP|AAC|AC3|DTS)\b']
GENERIC_LINK_TEXTS = ["资源链接", "直达链接", "下载", "点击", "天翼", "云盘", "分享", "链接", "百度网盘", "保存", "描述", "简介", "大小", "尺寸", "来自", "过期时间", "IMDb", "版权", "标签", "名称", "群组", "频道", "投稿"]

RE_ACCESS_CODE = re.compile(r'(?:密码|提取码|验证码|访问码|分享密码|密钥|pwd|password|share_pwd|pass_code)[(:：=\s]*([a-zA-Z0-9]{4,6})(?![a-zA-Z0-9])', re.IGNORECASE)
RE_URL_PARAM_CODE = re.compile(r'[?&](?:pwd|password|sharepwd)=([a-zA-Z0-9]{4,6})', re.IGNORECASE)
RE_TIANYI = re.compile(r'cloud\.189\.cn/.*\b(?:code=|t/)([a-zA-Z0-9]{12,})', re.IGNORECASE)
RE_UC = re.compile(r'drive\.uc\.cn/s/([a-zA-Z0-9\-_]+)', re.IGNORECASE)
RE_123 = re.compile(r'https?://[^\s/]*123[^\s/]*\.com/s/([a-zA-Z0-9\-_]+)', re.IGNORECASE)
RE_BAIDU = re.compile(r'(?:pan|yun)\.baidu\.com/(?:s/|share/init\?surl=)([a-zA-Z0-9\-_]+)', re.IGNORECASE)

# ==============================================================================
# ====== 辅助类与逻辑 ===========================================================
# ==============================================================================

class SQLiteManager:
    def __init__(self, db_path):
        self.db_file = os.path.join(db_path, "189api.db")
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS processed_msgs (channel_id TEXT, msg_id INTEGER, api_index INTEGER, timestamp REAL, PRIMARY KEY (channel_id, msg_id, api_index))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS sent_links (channel_id TEXT, link TEXT, api_index INTEGER, title TEXT, timestamp REAL, PRIMARY KEY (channel_id, link, api_index))''')
        self.conn.commit()

    def cleanup_old_records(self, days=30):
        cutoff = time.time() - (days * 86400)
        self.cursor.execute("DELETE FROM processed_msgs WHERE timestamp < ?", (cutoff,))
        self.conn.commit()

    def close(self): self.conn.close()
    
    def is_msg_processed(self, channel_id, msg_id):
        self.cursor.execute("SELECT 1 FROM processed_msgs WHERE channel_id=? AND msg_id=? LIMIT 1", (channel_id, msg_id))
        return self.cursor.fetchone() is not None

    def is_link_globally_sent(self, link, api_index):
        self.cursor.execute("SELECT 1 FROM sent_links WHERE link=? AND api_index=? LIMIT 1", (link, api_index))
        return self.cursor.fetchone() is not None

    def get_local_link_info(self, link, api_index, channel_id):
        self.cursor.execute("SELECT timestamp FROM sent_links WHERE channel_id=? AND link=? AND api_index=?", (channel_id, link, api_index))
        row = self.cursor.fetchone()
        if row: return {'exists': True, 'timestamp': row[0]}
        return {'exists': False, 'timestamp': 0}

    def add_link(self, link, api_index, title, channel_id, msg_timestamp):
        self.cursor.execute("INSERT OR REPLACE INTO sent_links (channel_id, link, api_index, title, timestamp) VALUES (?,?,?,?,?)", (channel_id, link, api_index, title, msg_timestamp))
        self.conn.commit()
            
    def bulk_add_msgs(self, data_list):
        if not data_list: return
        self.cursor.executemany("INSERT OR IGNORE INTO processed_msgs (channel_id, msg_id, api_index, timestamp) VALUES (?,?,?,?)", data_list)
        self.conn.commit()

class StringCleaner:
    @staticmethod
    def clean_basic(text):
        if not text: return ""
        text = re.sub(r'\[[^\]]+\]\(https?://[^\)]+\)', ' ', text)
        text = re.sub(r'https?://[^\s\u4e00-\u9fa5]+', '', text, flags=re.IGNORECASE)
        text = text.replace('**', '').replace('__', '').replace('`', '')
        for p in COMMON_AD_REGEX: text = re.sub(p, '', text, flags=re.IGNORECASE)
        text = re.sub(r'[@#]\S+', '', text)
        text = re.sub(r'^(链接|地址|百度网盘|天翼云盘)[:：]\s*$', '', text) 
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text) 
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9,，.。!！?？:：《》()（）【】\+\-\s\u3000&/_]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def is_junk_line(line):
        line = line.strip()
        if len(line) < 2 or line.startswith('http'): return True
        return any(kw in line for kw in JUNK_LINE_KEYWORDS)

    @staticmethod
    def is_generic_link_text(text):
        cleaned = StringCleaner.clean_basic(text)
        if not cleaned: return True
        clean_start = re.sub(r'^[\s\W]+', '', cleaned)
        for kw in GENERIC_LINK_TEXTS:
            if clean_start.startswith(kw): return True
        return False

    @staticmethod
    def count_chinese(text): return len(re.findall(r'[\u4e00-\u9fa5]', text))

class CloudMonitor:
    def __init__(self):
        self.db = SQLiteManager(SAVE_PATH)
        # ⚠️ 修复关键点：不要在 __init__ 里初始化 Semaphore，此时 Loop 可能不对
        self.sems = {}
        self.default_sem = None
        self.session_sent_links = set()

    async def start(self):
        print(">>> 初始化监控核心...")
        if not API_ID or not API_HASH or not STRING_SESSION:
            print("❌ 配置缺失: 请在Web界面填写 Telegram API 信息和 Session String。")
            return

        # 🌟 修复关键点：在 async start 内部初始化信号量，确保绑定到当前事件循环
        self.sems = {k: asyncio.Semaphore(v) for k, v in CONCURRENT_LIMITS.items() if k != 'default'}
        self.default_sem = asyncio.Semaphore(CONCURRENT_LIMITS.get('default', 5))

        self.db.cleanup_old_records(DB_RETENTION_DAYS)
        
        # 代理设置
        proxy_dict = None
        if ENABLE_PROXY and PROXY_URL:
            try:
                parsed = urlparse(PROXY_URL)
                scheme = parsed.scheme.lower()
                p_type_str = 'socks5'
                if 'http' in scheme: p_type_str = 'http'
                elif 'socks4' in scheme: p_type_str = 'socks4'
                
                proxy_dict = {
                    'proxy_type': p_type_str,
                    'addr': parsed.hostname,
                    'port': parsed.port,
                    'username': parsed.username,
                    'password': parsed.password,
                    'rdns': True 
                }
                print(f"🌐 代理已配置: [{p_type_str.upper()}] {parsed.hostname}:{parsed.port}")
            except Exception as e:
                print(f"❌ 代理配置错误: {e}")
        
        try:
            params = {'session': StringSession(STRING_SESSION), 'api_id': API_ID, 'api_hash': API_HASH}
            if proxy_dict: params['proxy'] = proxy_dict
            self.client = TelegramClient(**params)
            await self.client.start()
            me = await self.client.get_me()
            print(f"✅ Telegram 登录成功! 当前账号: {me.first_name} (ID: {me.id})")
        except Exception as e:
            print(f"❌ Telegram 登录失败: {e}")
            self.db.close()
            return

        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    await self.run_cycle(session)
                    print(f"💤 周期结束，休眠 {MONITOR_INTERVAL_HOURS} 小时...")
                    await asyncio.sleep(MONITOR_INTERVAL_HOURS * 3600)
        finally:
            await self.client.disconnect()
            self.db.close()

    async def run_cycle(self, session):
        print(f"\n⏰ [{datetime.now().strftime('%H:%M')}] 开始新一轮扫描...")
        for channel_url in CHANNEL_URLS:
            try:
                await self.process_channel(session, channel_url)
            except Exception as e:
                print(f"⚠️ 频道扫描出错 {channel_url}: {e}")

    async def process_channel(self, session, channel_url):
        clean_name = channel_url.strip().split('/')[-1].split('?')[0]
        cid = clean_name
        print(f"🔎 正在扫描频道: {clean_name}")
        
        entity = None
        # 1. 遍历对话列表
        try:
            async for dialog in self.client.iter_dialogs(limit=None):
                if dialog.entity.username and dialog.entity.username.lower() == clean_name.lower():
                    entity = dialog.entity
                    break
        except: pass

        # 2. 尝试获取
        if not entity:
            try:
                entity = await self.client.get_entity(clean_name)
            except:
                try:
                    result = await self.client(ResolveUsernameRequest(clean_name))
                    entity = result.chats[0] if result.chats else result.users[0]
                except:
                    print(f"⚠️ 找不到频道 [{clean_name}]，跳过。")
                    return

        # 尝试自动加入
        try: await self.client(JoinChannelRequest(entity)); 
        except: pass

        # 开始扫描
        min_date = datetime.now(timezone.utc) - timedelta(days=MONITOR_DAYS)
        consecutive_old_count = 0
        unique_resources = {}

        async for m in self.client.iter_messages(entity, limit=MONITOR_LIMIT):
            if m.date < min_date: break
            
            is_force = m.text and any(k in m.text for k in NOTIFY_KEYWORDS)
            if not is_force and self.db.is_msg_processed(str(entity.id), m.id):
                consecutive_old_count += 1
                if consecutive_old_count >= SMART_STOP_COUNT: break
            else:
                consecutive_old_count = 0
            
            if not m.text: continue
            infos = self.extract_links(m)
            if not infos: continue

            for info in infos:
                if info['link'] not in unique_resources:
                    unique_resources[info['link']] = {'msg': m, 'info': info}
                else:
                    if m.id > unique_resources[info['link']]['msg'].id:
                        unique_resources[info['link']] = {'msg': m, 'info': info}

        final_list = list(unique_resources.values())
        print(f"   ↳ 发现 {len(final_list)} 个资源，开始处理...")
        
        if final_list:
            await self._process_grouped_batch(session, final_list, clean_name, str(entity.id))

    def check_category_match(self, raw_text, cfg):
        priority = cfg.get('priority_keywords', [])
        if priority and any(k in raw_text for k in priority): return True
        req = cfg.get('required_keywords', [])
        if req and not all(k in raw_text for k in req): return False
        opt = cfg.get('optional_keywords', [])
        if opt and not any(k in raw_text for k in opt): return False
        return True

    def check_title_excluded(self, final_title, cfg):
        excluded = cfg.get('excluded_keywords', [])
        return any(kw in final_title for kw in excluded)

    async def _process_grouped_batch(self, session, grouped_items, channel_name, channel_id):
        tasks = []
        msgs_to_save = []
        now_ts = time.time()

        for item in grouped_items:
            msg = item['msg']
            info = item['info']
            
            if any(kw in msg.text for kw in EXCLUDE_KEYWORDS): continue
            msgs_to_save.append((channel_id, msg.id, 0, now_ts))
            msg_timestamp = msg.date.timestamp()

            for idx, cfg in enumerate(API_CONFIGS):
                if not self.check_category_match(msg.text, cfg): continue
                if self.check_title_excluded(info['desc'], cfg): break
                if self.db.is_link_globally_sent(info['link'], idx): break

                special = any(k in msg.text for k in cfg.get('priority_keywords', []))
                
                should_notify = False
                notify_type = ""
                if ENABLE_NOTIFY and NOTIFY_KEYWORDS:
                    if any(nk in info['desc'] for nk in NOTIFY_KEYWORDS):
                        local = self.db.get_local_link_info(info['link'], idx, channel_id)
                        if not local['exists']:
                            should_notify = True; notify_type = "🆕 新资源"
                        elif msg_timestamp > local['timestamp']:
                            should_notify = True; notify_type = "♻️ 资源更新"

                task_name = f"{cfg['folder_prefix']}{info['desc']}_{info['code'][-4:]}"[:200]
                payload = {"path": task_name, "shareId": info['code'], "folderId": "", "password": info['pwd'] or "", "type": info['type_id']}
                
                # 传入 key 用于并发控制
                tasks.append(self.push_wrapper(session, payload, info, idx, special, channel_name, should_notify, notify_type, msg_timestamp, channel_id, info['key']))
                break 
        
        if tasks: await asyncio.gather(*tasks)
        self.db.bulk_add_msgs(msgs_to_save)

    async def push_wrapper(self, session, payload, info, idx, special, channel_name, should_notify, notify_type, msg_timestamp, channel_id, sem_key):
        # 使用对应的信号量
        sem = self.sems.get(sem_key, self.default_sem)
        async with sem:
            headers = {"x-api-key": ALIST_KEY, "Content-Type": "application/json", "Authorization": ALIST_KEY}
            try:
                async with session.post(ALIST_URL, json=payload, headers=headers, timeout=20) as r:
                    if r.status == 200:
                        print(f"✅ 推送成功: {info['desc'][:40]}")
                        self.db.add_link(info['link'], idx, info['desc'], channel_id, msg_timestamp)
                        if should_notify:
                            await self.send_telegram_notify(session, notify_type, info['desc'], info['link'], payload['password'], channel_name)
                    elif r.status == 400:
                        print(f"⚠️ 资源已存在: {info['desc'][:40]}")
                        self.db.add_link(info['link'], idx, info['desc'], channel_id, msg_timestamp)
                    else:
                        print(f"❌ 推送失败 {r.status}: {info['desc'][:40]}")
            except Exception as e:
                print(f"💥 请求异常: {e}")

    async def send_telegram_notify(self, session, type_str, title, link, pwd, channel_name):
        if not BOT_TOKEN or not BOT_CHAT_ID: return
        pwd_str = f" (`{pwd}`)" if pwd else ""
        msg_body = f"*{type_str}*\n\n🎬 *标题:* `{title}`\n📢 *来源:* `{channel_name}`\n🔗 *链接:* {link}{pwd_str}\n📅 *时间:* {datetime.now().strftime('%H:%M:%S')}"
        try:
            async with session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": BOT_CHAT_ID, "text": msg_body, "parse_mode": "Markdown"}) as resp: pass
        except: pass

    def extract_links(self, msg):
        raw = msg.message.replace('%EF%BC%88', '(').replace('%EF%BC%89', ')')
        clean_lines = [StringCleaner.clean_basic(l) for l in raw.split('\n')]
        title = "Untitled"; title_idx = 0
        for i, l in enumerate(clean_lines):
            if not l: continue 
            title_idx = i
            title = re.sub(r'^[\s\W]*(名称|标题|资源|剧名|片名|中文名)[:：]\s*', '', l)
            break 

        m_pwd = RE_ACCESS_CODE.search(raw)
        global_pwd = m_pwd.group(1) if m_pwd else None
        
        patterns = []
        if ENABLE_189: patterns.append((RE_TIANYI, 9, 'a189', "https://cloud.189.cn/t/"))
        if ENABLE_BAIDU: patterns.append((RE_BAIDU, 10, 'baidu', "https://pan.baidu.com/s/"))
        if ENABLE_UC: patterns.append((RE_UC, 7, 'uc', "https://drive.uc.cn/s/"))
        if ENABLE_123: patterns.append((RE_123, 3, 'a123', "https://www.123865.com/s/"))

        items = []
        line_offsets = []
        current_offset = 0
        for line in raw.split('\n'):
            line_offsets.append(current_offset)
            current_offset += len(line) + 1

        def get_line_idx(offset):
            idx = bisect.bisect_right(line_offsets, offset) - 1
            return idx if idx >= 0 else 0

        for p, tid, key, prefix in patterns:
            for m in p.finditer(raw):
                line_idx = get_line_idx(m.start())
                # 增加 'key' 字段用于并发控制
                items.append({'code': m.group(1), 'type_id': tid, 'key': key, 'prefix': prefix, 'match_str': m.group(0), 'is_entity': False, 'line_idx': line_idx})
            if msg.entities:
                for e in [x for x in msg.entities if isinstance(x, MessageEntityTextUrl)]:
                    if p.search(e.url):
                        line_idx = get_line_idx(e.offset)
                        items.append({'code': p.search(e.url).group(1), 'type_id': tid, 'key': key, 'prefix': prefix, 'match_str': e.url, 'is_entity': True, 'entity_text': raw[e.offset:e.offset+e.length], 'line_idx': line_idx})

        if msg.reply_markup and hasattr(msg.reply_markup, 'rows'):
            for row in msg.reply_markup.rows:
                for button in row.buttons:
                    if isinstance(button, KeyboardButtonUrl) and button.url:
                        for p, tid, key, prefix in patterns:
                            m = p.search(button.url)
                            if m:
                                items.append({'code': m.group(1), 'type_id': tid, 'key': key, 'prefix': prefix, 'match_str': button.url, 'is_entity': False, 'line_idx': -1})

        if not items: return []
        base_title = StringCleaner.clean_basic(title)
        if not base_title: base_title = "Untitled_Resource"
        is_multi = len(set(i['code'] for i in items)) > 1
        results = []; seen = set()
        for it in items:
            if it['code'] in seen: continue
            seen.add(it['code'])
            m_url_pwd = RE_URL_PARAM_CODE.search(it['match_str'])
            pwd = m_url_pwd.group(1) if m_url_pwd else global_pwd
            final_code = it['code']
            if it['key'] == 'baidu': 
                if 'init' in it['match_str'] or len(final_code) == 22:
                     if not final_code.startswith('1'): final_code = '1' + final_code

            sub = ""
            if is_multi and it['line_idx'] >= 0:
                idx = it['line_idx']
                if len(clean_lines[idx]) > 2 and not StringCleaner.is_generic_link_text(clean_lines[idx]): 
                    sub = clean_lines[idx]
                elif idx > 0 and len(clean_lines[idx-1]) > 2 and not StringCleaner.is_junk_line(clean_lines[idx-1]) and not StringCleaner.is_generic_link_text(clean_lines[idx-1]):
                    sub = clean_lines[idx-1]

            if (not sub) and (not is_multi or it['line_idx'] == -1 or it.get('entity_text') == title):
                for l in clean_lines[title_idx+1:]:
                    if len(l) < 2: continue
                    if StringCleaner.is_junk_line(l): continue
                    if StringCleaner.is_generic_link_text(l): continue 
                    if StringCleaner.count_chinese(l) > 30: continue 
                    if 'IMDB' not in l: 
                        sub = l; break

            final = base_title
            if sub and sub != base_title: final = f"{base_title} {sub}" if is_multi else (sub if base_title in sub else f"{base_title} {sub}")
            results.append({'type_id': it['type_id'], 'key': it['key'], 'code': final_code, 'link': f"{it['prefix']}{it['code']}", 'pwd': pwd, 'desc': final})
        return results

if __name__ == '__main__':
    try: asyncio.run(CloudMonitor().start())
    except KeyboardInterrupt: pass