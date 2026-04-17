import aiohttp
import re
from urllib.parse import quote

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger, AstrBotConfig

TAOBAO_REGEX = re.compile(
    r'(https?://[^\s<>]*(?:taobao\.|tb\.)[^\s<>]+)|'
    r'(?:￥|\$)([0-9A-Za-z()]*[A-Za-z][0-9A-Za-z()]{10})(?:￥|\$)?(?![0-9A-Za-z])|'
    r'tk=([0-9A-Za-z]{11,12})'
)

JD_REGEX = re.compile(
    r'https?:\/\/[^\s<>]*(3\.cn|jd\.|jingxi)[^\s<>]+|[^一-龥0-9a-zA-Z=;&?-_.<>:\'",{}][0-9a-zA-Z()]{16}[^一-龥0-9a-zA-Z=;&?-_.<>:\'",{}\s]'
)

class XinxinRebatePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.processed_titles = set()
        logger.info("xinxin返利 插件已挂载 (支持 openclaw-weixin 通道)！")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_rebate_message(self, event: AstrMessageEvent):
        # 1. 防止机器人无限自循环回复（抓取自身发出的消息）
        if event.get_sender_id() == event.bot.self_id:
            return

        msg_str = event.message_str.strip()
        if not msg_str:
            return

        results = []

        # 2. 正则提取与转链
        for match in TAOBAO_REGEX.finditer(msg_str):
            token = next((m for m in match.groups() if m), None)
            if token:
                res = await self.convert_tkl(token)
                if res: results.append(res)

        for match in JD_REGEX.finditer(msg_str):
            token = match.group(0)
            res = await self.convert_jd_link(token)
            if res: results.append(res)

        # 3. 直接通过 openclaw 接口向当前微信会话返回文本
        if results:
            reply_content = "\n\n".join(results)
            yield event.plain_result(reply_content)
            
            # 【关键操作】拦截事件！
            # 防止微信里的 AI 大模型（比如 DeepSeek/GPT）接着这条消息继续“瞎分析”
            event.stop_event()

    async def convert_tkl(self, tkl: str):
        appkey = self.config.get("taobao_app_key", "")
        sid = self.config.get("taobao_sid", "")
        pid = self.config.get("taobao_pid", "")
        relation_id = self.config.get("taobao_relation_id", "")

        if not appkey or not pid:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                base_url = "https://api.zhetaoke.com:10001/api/open_gaoyongzhuanlian_tkl.ashx"
                params = {
                    "appkey": appkey, "sid": sid, "pid": pid,
                    "relation_id": relation_id, "tkl": quote(tkl), "signurl": 5
                }
                async with session.get(base_url, params=params, timeout=5.0) as resp:
                    if resp.status != 200: return None
                    result = await resp.json(content_type=None)
                    
                    if result.get("status") == 200 and "content" in result:
                        content = result["content"][0]
                        title = content.get('tao_title', content.get('title', '未知'))
                        
                        if title in self.processed_titles: return None
                        self.processed_titles.add(title)
                        
                        return (
                            f"【淘宝】{title}\n"
                            f"💰 券后价: ￥{content.get('quanhou_jiage', '未知')}\n"
                            f"🎁 预计返佣: ￥{content.get('tkfee3', '未知')}\n"
                            f"👉 淘口令: {content.get('tkl', '未知')}"
                        )
        except Exception as e:
            logger.error(f"淘宝转链异常: {e}")
        return None

    async def convert_jd_link(self, material_url: str):
        jd_appkey = self.config.get("jd_appkey", "")
        union_id = self.config.get("jd_union_id", "")
        position_id = self.config.get("jd_position_id", "")
        jtt_appid = self.config.get("jtt_appid", "")
        jtt_appkey = self.config.get("jtt_appkey", "")

        if not jd_appkey or not union_id:
            return None

        try:
            async with aiohttp.ClientSession() as session:
                base_url = "http://api.zhetaoke.com:20000/api/open_jing_union_open_promotion_byunionid_get.ashx"
                params = {
                    "appkey": jd_appkey, "materialId": material_url, 
                    "unionId": union_id, "positionId": position_id, "chainType": 3, "signurl": 5
                }
                async with session.get(base_url, params=params, timeout=5.0) as resp:
                    if resp.status != 200: return None
                    result = await resp.json(content_type=None)
                    
                    if result.get("status") == 200 and "content" in result:
                        content = result["content"][0]
                        jianjie = content.get('jianjie', '未知')
                        
                        if jianjie in self.processed_titles: return None
                        self.processed_titles.add(jianjie)
                        
                        short_url = content.get('shorturl', '')
                        jd_command_text = ""
                        
                        if short_url and jtt_appid and jtt_appkey:
                            jtt_url = f"http://japi.jingtuitui.com/api/get_goods_command?appid={jtt_appid}&appkey={jtt_appkey}&unionid={union_id}&gid={quote(short_url)}"
                            if position_id: jtt_url += f"&positionid={position_id}"
                            try:
                                async with session.post(jtt_url, timeout=3.0) as cmd_resp:
                                    cmd_result = await cmd_resp.json(content_type=None)
                                    if "return" in cmd_result and cmd_result.get("msg", "").startswith("ok"):
                                        jd_kl = cmd_result["return"].get("jd_short_kl", "")
                                        if jd_kl: jd_command_text = f"\n👉 领券口令: {jd_kl}"
                            except Exception as e:
                                pass

                        return (
                            f"【京东】{jianjie}\n"
                            f"💰 券后价: ￥{content.get('quanhou_jiage', '未知')}\n"
                            f"🎁 预计返佣: ￥{content.get('tkfee3', '未知')}\n"
                            f"🔗 点击抢购: {short_url}"
                            f"{jd_command_text}"
                        )
        except Exception as e:
            logger.error(f"京东转链异常: {e}")
        return None
