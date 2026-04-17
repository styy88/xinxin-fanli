import aiohttp
import re
import json
import hashlib
import time
from urllib.parse import quote, unquote
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger, AstrBotConfig

class XinxinFanli(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def handle_rebate_message(self, event: AstrMessageEvent):
        if event.get_sender_id() == event.message_obj.self_id:
            return
        
        msg = event.message_str.strip()
        if not msg or msg.startswith("/"):
            return

        # 平台识别
        is_taobao = any(kw in msg for kw in ["tb.cn", "taobao.com", "tmall.com", "￥", "$"])
        is_jd = any(kw in msg for kw in ["jd.com", "3.cn"])
        is_pdd = any(kw in msg for kw in ["yangkeduo.com", "pinduoduo.com", "p.pinduoduo.com", "goods1.html"])

        res = None
        try:
            if is_taobao:
                logger.info("[小新返利] 🎯 识别淘宝文案")
                res = await self.get_taobao_rebate(msg)
            elif is_jd:
                logger.info("[小新返利] 🎯 识别京东 (折京客全能接口)")
                res = await self.get_jd_zhetaoke_rebate(msg)
            elif is_pdd:
                logger.info("[小新返利] 🎯 识别拼多多 (官方接口模式)")
                res = await self.pdd_official_flow(msg, event.get_sender_id())
        except Exception as e:
            logger.error(f"[小新返利] 处理流程异常: {e}")
            return

        if res:
            yield event.plain_result(res)
            event.stop_event()
        elif is_taobao or is_jd or is_pdd:
            event.stop_event()

    # --- 京东逻辑：折京客全能版 ---
    async def get_jd_zhetaoke_rebate(self, content: str):
        c = self.config
        appkey = c.get("taobao_app_key")  # 折淘客通用 AppKey
        union_id = c.get("jd_union_id")   # 京东联盟 ID
        
        if not all([appkey, union_id]):
            return "❌ 京东配置不全：请确保填写了折淘客 AppKey 和 京东联盟 ID"

        # 提取物料链接并进行 URL 编码
        url_match = re.search(r'https?://[^\s]+', content)
        material_id = url_match.group(0) if url_match else content

        # 接口参数
        params = {
            "appkey": appkey,
            "materialId": material_id, # aiohttp 会自动对 params 进行编码
            "unionId": union_id,
            "chainType": 3,   # 返回长短链
            "signurl": 5      # 开启聚合模式，自动匹配详情和券
        }

        async with aiohttp.ClientSession() as session:
            # 使用折淘客 20000 端口京东专用接口
            api_url = "http://api.zhetaoke.com:20000/api/open_jing_union_open_promotion_byunionid_get.ashx"
            try:
                async with session.post(api_url, data=params, timeout=12) as resp:
                    res_text = await resp.text()
                    data = json.loads(res_text.strip().lstrip('\ufeff'))
                    
                    if data.get("status") == 200 and data.get("content"):
                        item = data["content"][0]
                        return (f"✨【京东】{item.get('tao_title') or item.get('title')}\n"
                                f"💰 原价: ￥{item.get('size')}\n"
                                f"🔥 券后价: ￥{item.get('quanhou_jiage')}\n"
                                f"🎁 优惠券: {item.get('coupon_info', '暂无')}\n"
                                f"🔗 直达链接: {item.get('shorturl') or item.get('coupon_click_url')}")
                    
                    # 如果 signurl=5 没结果，尝试解析官方原生返回格式
                    if "jd_union_open_promotion_byunionid_get_response" in data:
                        res_str = data["jd_union_open_promotion_byunionid_get_response"].get("result", "{}")
                        res_obj = json.loads(res_str)
                        if res_obj.get("code") == 200:
                            link = res_obj.get("data", {}).get("shortURL")
                            return f"✨【京东】专属优惠已生成\n🔗 链接：{link}"

            except Exception as e:
                logger.error(f"[小新返利] 京东折淘客请求异常: {e}")
        return "⚠️ 京东解析失败：该商品可能没有佣金或链接无法识别。"

    # --- 拼多多逻辑：官方原生版 (已通过备案测试) ---
    def _generate_pdd_sign(self, params: dict, secret: str) -> str:
        sorted_keys = sorted(params.keys())
        string_to_sign = secret
        for key in sorted_keys:
            string_to_sign += f"{key}{params[key]}"
        string_to_sign += secret
        return hashlib.md5(string_to_sign.encode('utf-8')).hexdigest().upper()

    async def pdd_official_flow(self, content: str, user_id: str):
        c = self.config
        pid, secret, cl_id = c.get("pdd_pid"), c.get("pdd_app_secret"), c.get("pdd_app_key")
        uid = c.get("pdd_custom_parameters") or user_id
        c_params = json.dumps({"uid": str(uid)}, separators=(',', ':'))

        async def pdd_call(api, biz):
            p = {"type": api, "client_id": cl_id, "timestamp": str(int(time.time())), "data_type": "JSON"}
            p.update(biz)
            p["sign"] = self._generate_pdd_sign(p, secret)
            async with aiohttp.ClientSession() as s:
                async with s.post("https://gw-api.pinduoduo.com/api/router", data=p) as r:
                    return json.loads((await r.text()).strip().lstrip('\ufeff'))

        q = await pdd_call("pdd.ddk.member.authority.query", {"pid": pid, "custom_parameters": c_params})
        if q.get("authority_query_response", {}).get("bind", 0) == 0:
            auth = await pdd_call("pdd.ddk.rp.prom.url.generate", {"channel_type": 10, "p_id_list": json.dumps([str(pid)]), "custom_parameters": c_params})
            try: return f"🏮 拼多多备案提醒\n🔗 请先授权：{auth['rp_promotion_url_generate_response']['url_list'][0]['short_url']}"
            except: return "❌ 拼多多授权生链失败"

        url_m = re.search(r'https?://[^\s]+', content)
        z = await pdd_call("pdd.ddk.goods.zs.unit.url.gen", {"pid": pid, "source_url": url_m.group(0) if url_m else content, "custom_parameters": c_params})
        res = z.get("goods_zs_unit_generate_response")
        if res: return f"✨【拼多多】优惠已生成\n🔗 领券地址：{res.get('mobile_short_url') or res.get('short_url')}"
        return "❌ 拼多多转链失败"

    # --- 淘宝逻辑：折淘客版 ---
    async def get_taobao_rebate(self, content: str):
        c = self.config
        p = {"appkey": c.get("taobao_app_key"), "sid": c.get("taobao_sid"), "pid": c.get("taobao_pid"), "tkl": content, "signurl": 5, "relation_id": c.get("taobao_relation_id", "")}
        async with aiohttp.ClientSession() as s:
            try:
                async with s.get("https://api.zhetaoke.com:10001/api/open_gaoyongzhuanlian_tkl.ashx", params=p) as r:
                    data = json.loads((await r.text()).strip().lstrip('\ufeff'))
                    if data.get("status") == 200 and data.get("content"):
                        i = data["content"][0]
                        return f"✨【淘宝】{i.get('tao_title')}\n💰券后: ￥{i.get('quanhou_jiage')}\n🔗领券: {i.get('shorturl2') or i.get('shorturl')}\n📝口令: {i.get('tkl')}"
            except: pass
        return None
