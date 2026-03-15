import requests
import json
import hashlib
import time
import random
import os
from datetime import datetime
from pathlib import Path

# ================= 全局配置区 =================
# 【核心开关】统一修改所有账号执行的方法
GLOBAL_METHOD = "add.signon.item"# 签到方法
# GLOBAL_METHOD = "get.signon.list"#这个是签到天数的
GLOBAL_STYPE = 1

# 【通知配置】企业微信 Webhook 地址
# 请替换为你自己的 key (替换掉示例中的 key)
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=693axxx6-848f-49ba-a110-20ae080baf95"

# 【调试开关】True: 打印完整返回JSON; False: 仅失败时打印66cc63a1-0679-9888-3146-0b13a88d9901
SHOW_RAW_RESPONSE = True

SECRET = "36affdc58f50e1035649abc808c22b48"
APPKEY = "76472358"
PLATFORM = "MP-WEIXIN"
FORMAT = "json"
URL = "https://service.milwaukeetool.cn/api/v1/signon"

HEADERS = {
    "Host": "service.milwaukeetool.cn",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541739) XWEB/18955",
    "xweb_xhr": "1",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://servicewechat.com/wxc13e77b0a12aac68/59/page-frame.html",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9"
}


# ===========================================

def generate_sign(params_dict):
    sorted_keys = sorted(params_dict.keys())
    s = SECRET
    for key in sorted_keys:
        val = params_dict[key]
        if isinstance(val, bool):
            val = 1 if val else 0
        s += str(key) + str(val)
    s += SECRET
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def send_wechat_notification(failed_accounts, total_count, success_count):
    """发送企业微信通知"""
    if not WEBHOOK_URL or "key=693axxx6" in WEBHOOK_URL:
        print("\n⚠️  未配置有效的 Webhook URL，跳过通知发送。")
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 构建失败详情列表
    fail_details = "\n".join([f"• {name}: {reason}" for name, reason in failed_accounts])

    content = (
        f"🤖 **签到任务执行报告**\n"
        f"📅 时间: {now_str}\n"
        f"--------------------------\n"
        f"✅ 成功: {success_count} 个\n"
        f"❌ 失败: {len(failed_accounts)} 个\n"
        f"📂 总数: {total_count} 个\n"
        f"--------------------------\n"
        f"⚠️ **失败详情:**\n{fail_details}"
    )

    payload = {
        "msgtype": "text",
        "text": {
            "content": content
        }
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if resp.status_code == 200 and resp.json().get("errcode") == 0:
            print("\n📢 已发送失败通知到企业微信。")
        else:
            print(f"\n⚠️  通知发送失败: {resp.text}")
    except Exception as e:
        print(f"\n⚠️  通知发送异常: {str(e)}")


def process_account(account_info, index, total, failed_list):
    token = os.getenv('MILWAUKEETOOL_TOKEN_LIST', '')
    client_id = os.getenv('MILWAUKEETOOL_CLIENT_ID', '')
    token_show = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else "***"

    print(f"      ├─ 方法: {GLOBAL_METHOD}")
    print(f"      ├─ ID: {client_id}")
    print(f"      └─ Token: {token_show}")

    if not token or not client_id:
        msg = "缺少 token 或 client_id"
        print(f"      ❌ 结果: {msg}")
        failed_list.append((name, msg))
        return False

    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "token": token,
        "client_id": client_id,
        "appkey": APPKEY,
        "format": FORMAT,
        "timestamp": timestamp_str,
        "platform": PLATFORM,
        "method": GLOBAL_METHOD
    }

    if GLOBAL_METHOD == "add.signon.item":
        payload["year"] = str(now.year)
        payload["month"] = str(now.month)
        payload["day"] = str(now.day)
        payload["stype"] = GLOBAL_STYPE

    sign_val = generate_sign(payload)
    payload["sign"] = sign_val

    try:
        delay = random.uniform(1.0, 2.5)
        print(f"      ⏳ 等待 {delay:.1f}s...")
        time.sleep(delay)

        response = requests.post(URL, headers=HEADERS, json=payload, timeout=10)
        resp_json = response.json()

        code = resp_json.get("code")
        msg = resp_json.get("msg", "") or resp_json.get("message", "") or str(resp_json)

        is_success = False
        if code == 200:
            is_success = True
        elif "success" in str(resp_json).lower():
            is_success = True
        elif GLOBAL_METHOD == "add.signon.item" and ("已签到" in msg or "成功" in msg or "重复" in msg):
            is_success = True

        if is_success:
            print(f"      ✅ 结果: 成功 | {msg}")
            if SHOW_RAW_RESPONSE:
                print(f"      └─ 返回: {json.dumps(resp_json, ensure_ascii=False)}")
        else:
            print(f"      ⚠️ 结果: 失败 (Code:{code}) | {msg}")
            # 失败时强制打印完整返回
            print(f"      └─ 完整返回:\n{json.dumps(resp_json, ensure_ascii=False, indent=4)}")

            # 记录失败信息用于通知
            short_msg = msg if len(msg) < 50 else msg[:47] + "..."
            failed_list.append((name, f"{short_msg} (Code:{code})"))
            return False

    except Exception as e:
        err_msg = str(e)
        print(f"      ❌ 结果: 网络/系统错误 - {err_msg}")
        failed_list.append((name, f"网络错误: {err_msg}"))
        return False

    try:
        print(f"      ⏳ 檢查簽到..等待 {delay:.1f}s...")
        time.sleep(delay)

        response = requests.post('https://service.milwaukeetool.cn/api/v1/signon', headers=HEADERS, json=payload, timeout=20)
        resp_json = response.json()

        code = resp_json.get("code")
        msg = str(resp_json)
        print(f"      └─ 返回: {json.dumps(resp_json, ensure_ascii=False)}")
        
        else:
            # print(f"      ⚠️ 檢查簽到结果: 失败 (Code:{code}) | {msg}")
            # 失败时强制打印完整返回
            # print(f"      └─ 完整返回:\n{json.dumps(resp_json, ensure_ascii=False, indent=4)}")

            # 记录失败信息用于通知
            # short_msg = msg if len(msg) < 50 else msg[:47] + "..."
            # failed_list.append((name, f"{short_msg} (Code:{code})"))
            return False

    except Exception as e:
        err_msg = str(e)
        print(f"      ❌ 结果: 网络/系统错误 - {err_msg}")
        failed_list.append((name, f"网络错误: {err_msg}"))
        return False


def main():
    print("=" * 60)
    print(f"🚀 批量签到启动 | 模式: {GLOBAL_METHOD}")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_count = 0
    failed_list = []  # 存储 (名字, 原因)

    process_account(0, 1, 1, failed_list)

    # for i, acc in enumerate(accounts, 1):
    #     if process_account(acc, i, len(accounts), failed_list):
    #         success_count += 1

    # 汇总
    print("\n" + "=" * 60)
    print(f"🏁 任务结束")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ❌ 失败: {len(failed_list)}")
    print("=" * 60)

    # 如果有失败，发送通知
    if len(failed_list) > 0:
        print("\n失敗。")
    else:
        print("\n🎉 全部成功，无需发送通知。")


if __name__ == "__main__":
    main()
