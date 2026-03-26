import requests
import json
import hashlib
import time
import random
import os
from datetime import datetime
from pathlib import Path

# ================= 全局配置区 =================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

MILWAUKEETOOL_TOKEN_LIST = os.getenv('MILWAUKEETOOL_TOKEN_LIST', '')
MILWAUKEETOOL_CLIENT_ID = os.getenv('MILWAUKEETOOL_CLIENT_ID', '')

# 【签到配置】
SIGNON_URL = "https://service.milwaukeetool.cn/api/v1/signon"
SIGNON_METHOD = "add.signon.item"
GLOBAL_STYPE = 1

# 【查询配置】
QUERY_URL = "https://service.milwaukeetool.cn/api/v1/user"
QUERY_METHOD = "get.user.item"

# 【通知配置】企业微信 Webhook 地址 (可选)
WEBHOOK_URL = ""  # 如果需要通知，请填入 key

# 【调试开关】
SHOW_RAW_RESPONSE = False

# 【公共密钥】
SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"

# 【公共请求头】
HEADERS = {
    "Host": "service.milwaukeetool.cn",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/527.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541739) XWEB/18945",
    "xweb_xhr": "1",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://servicewechat.com/wxc13e77b0a12aac68/59/page-frame.html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9"
}


# ================= 核心功能函数 =================

def generate_sign(params_dict):
    """生成签名"""
    sorted_keys = sorted(params_dict.keys())
    s = SECRET
    for key in sorted_keys:
        val = params_dict[key]
        if isinstance(val, bool):
            val = 1 if val else 0
        s += str(key) + str(val)
    s += SECRET
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def do_signon(token, client_id):
    """执行签到操作"""
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": SIGNON_METHOD,
        "year": str(now.year),
        "month": str(now.month),
        "day": str(now.day),
        "stype": GLOBAL_STYPE
    }

    payload["sign"] = generate_sign(payload)

    try:
        response = requests.post(SIGNON_URL, headers=HEADERS, json=payload, timeout=10)
        resp_json = response.json()

        code = resp_json.get("code")
        msg = resp_json.get("msg", "") or resp_json.get("message", "")

        # 判断成功逻辑
        is_success = False
        if code == 200:
            is_success = True
        elif "success" in str(resp_json).lower():
            is_success = True
        elif "已签到" in msg or "成功" in msg or "重复" in msg:
            is_success = True

        if is_success:
            return True, msg
        else:
            return False, f"{msg} (Code:{code})"
    except Exception as e:
        return False, str(e)


def get_points(token, client_id):
    """查询积分操作"""
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": QUERY_METHOD
    }

    payload["sign"] = generate_sign(payload)

    try:
        response = requests.post(QUERY_URL, data=json.dumps(payload), headers=HEADERS, timeout=10)
        resp_json = response.json()

        # 提取积分
        points = resp_json.get("data", {}).get("get_user_money", {}).get("points")
        mobile = resp_json.get("data", {}).get("mobile", "未知")

        if points is not None:
            return True, points, mobile
        else:
            msg = resp_json.get("message") or resp_json.get("msg") or "无积分字段"
            return False, 0, msg
    except Exception as e:
        return False, 0, str(e)


def process_account(token, client_id, index, total, failed_list):
    """处理单个账号：签到 -> 查询"""
    token_show = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"

    print(f"\n[{index}/{total}] 正在处理: {token_show}")
    print(f"      ├─ ID: {client_id}")

    # --- 第一步：签到 ---
    print(f"      📝 [1/2] 正在签到...")
    # 随机延时防封
    delay = random.uniform(0.5, 1.5)
    time.sleep(delay)

    sign_success, sign_msg = do_signon(token, client_id)

    if sign_success:
        print(f"      ✅ 签到结果: {sign_msg}")
    else:
        print(f"      ⚠️ 签到异常: {sign_msg}")
        # 签到失败也记录，但不一定中断后续查询

    # --- 第二步：查询积分 ---
    print(f"      💰 [2/2] 正在查询积分...")
    time.sleep(0.5)  # 短暂延时

    query_success, points, extra_info = get_points(token, client_id)

    if query_success:
        print(f"      ✅ 当前积分: {points} (手机: {extra_info})")
        # 如果签到失败但查询成功，视为部分成功，不加入失败列表用于通知，除非业务要求严格
        if not sign_success:
            failed_list.append((client_id, f"签到失败({sign_msg}), 但查询成功"))
        return sign_success, points
    else:
        print(f"      ❌ 查询失败: {extra_info}")
        failed_list.append((client_id, f"查询失败: {extra_info}"))
        return False, 0


def send_wechat_notification(failed_accounts, total_count, success_count, total_points):
    """发送企业微信通知"""
    if not WEBHOOK_URL:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fail_details = "\n".join([f"• {client_id}: {reason}" for client_id, reason in failed_accounts])

    content = (
        f"🤖 **签到 & 积分报告**\n"
        f"📅 时间: {now_str}\n"
        f"--------------------------\n"
        f"✅ 成功: {success_count} 个\n"
        f"❌ 失败: {len(failed_accounts)} 个\n"
        f"💰 总积分: {total_points}\n"
        f"--------------------------\n"
        f"⚠️ **失败详情:**\n{fail_details}"
    )

    payload = {"msgtype": "text", "text": {"content": content}}

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("errcode") == 0:
            print("\n📢 已发送通知到企业微信。")
    except Exception as e:
        print(f"\n⚠️ 通知发送异常: {str(e)}")


def send_telegram_notification(failed_accounts, total_count, success_count, total_points):
    """发送Telegram通知"""

    # Telegram
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n❌ 错误: 未配置Telegram通知，请检查环境变量。")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fail_details = "\n".join([f"• {client_id}: {reason}" for client_id, reason in failed_accounts])

    content = (
        f"🤖 **签到 & 积分报告**\n"
        f"📅 时间: {now_str}\n"
        f"--------------------------\n"
        f"✅ 成功: {success_count} 个\n"
        f"❌ 失败: {len(failed_accounts)} 个\n"
        f"💰 总积分: {total_points}\n"
        f"--------------------------\n"
        f"⚠️ **失败详情:**\n{fail_details}"
    )

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        params = {'chat_id': TELEGRAM_CHAT_ID, 'text': content}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("\n📢 Telegram-通知已推送。")
        else:
            print(f"\n⚠️ Telegram-通知发送异常: {response.status_code} {response.text}")
    except Exception as e:
        print(f"\n⚠️ 通知发送异常: {str(e)}")

def main():
    print("=" * 60)
    print("🚀 美沃奇自动签到 + 积分查询工具")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


    tokenList = [token.strip() for token in MILWAUKEETOOL_TOKEN_LIST.split(',') if token.strip()]
    clientIdList = [id.strip() for id in MILWAUKEETOOL_CLIENT_ID.split(',') if id.strip()]

    print(f"📂 共加载 {len(tokenList)} 个账号\n")

    success_count = 0
    total_points = 0
    failed_list = []

    for idx, (token, client_id) in enumerate(zip(tokenList, clientIdList), 1):
        is_success, points = process_account(token, client_id, idx, len(tokenList), failed_list)

        if is_success:
            success_count += 1
        total_points += points

        # 账号间大延时，防止频率限制
        if idx < len(tokenList):
            wait_time = random.uniform(2.0, 4.0)
            print(f"      ⏳ 等待 {wait_time:.1f}s 后处理下一个账号...")
            time.sleep(wait_time)

    # 汇总
    print("\n" + "=" * 60)
    print("🏁 任务结束")
    print(f"   ✅ 签到成功: {success_count} / {len(tokenList)}")
    print(f"   💰 累计积分: {total_points}")
    if failed_list:
        print(f"   ❌ 异常账号: {len(failed_list)}")
    print("=" * 60)

    if failed_list:
        print("\n⚠️ 异常详情:")
        for client_id, reason in failed_list:
            print(f"   • {client_id}: {reason}")

        send_wechat_notification(failed_list, len(tokenList), success_count, total_points)
        send_telegram_notification(failed_list, len(tokenList), success_count, total_points)
    else:
        print("\n🎉 全部执行成功！")


if __name__ == "__main__":
    main()
