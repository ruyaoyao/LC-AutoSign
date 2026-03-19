import requests
from requests.exceptions import RequestException
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

MILWAUKEETOOL_TOKEN_LIST = os.getenv('MILWAUKEETOOL_TOKEN_LIST', '')
MILWAUKEETOOL_CLIENT_ID = os.getenv('MILWAUKEETOOL_CLIENT_ID', '')
SEND_KEY_LIST = os.getenv('SEND_KEY_LIST', '')

FAILED_LOG = []
RESULT_LOG = []

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf2541739) XWEB/18955",
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

def format_sign_status(json_data, client_id=None):
    """
    將簽到狀態 JSON 資料格式化為易讀的文字
    """
    try:
        # 解析 JSON
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # 檢查回應狀態
        if data.get('status') != 200:
            cid = f" | client_id: {client_id}" if client_id is not None else ""
            return f"❌ 錯誤：API 回應異常 (狀態碼: {data.get('status')}){cid}"

        # 取得簽到資料
        sign_data = data.get('data', {})
        sign_status = sign_data.get('SigninStatus', 0)
        sign_count = sign_data.get('signcount', 0)
        items = sign_data.get('items', [])
        send_num = sign_data.get('send_num', 0)
        used_num = sign_data.get('used_num', 0)
        available_num = sign_data.get('available_send_num', 0)

        # 格式化輸出
        output = []
        output.append("=" * 50)
        output.append(" 📋 簽到系統狀態報告 ".center(48, "="))
        output.append("=" * 50)
        output.append("")

        # 基本狀態
        status_text = "✅ 已簽到" if sign_status == 1 else "❌ 未簽到"
        output.append(f"【基本資訊】")
        if client_id is not None:
            output.append(f"  🆔 client_id：{client_id}")
        output.append(f"  🔐 簽到狀態：{status_text}")
        output.append(f"  📊 連續簽到：{sign_count} 天")
        output.append(f"  📅 簽到總數：{len(items)} 天")
        output.append("")

        # 簽到記錄
        if items:
            output.append("【簽到記錄】")
            # 排序日期
            sorted_items = sorted(items)

            # 找出缺失的日期
            if len(sorted_items) > 1:
                try:
                    date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_items]
                    missing_dates = []
                    for i in range(len(date_objs) - 1):
                        current = date_objs[i]
                        next_date = date_objs[i + 1]
                        days_diff = (next_date - current).days
                        if days_diff > 1:
                            for j in range(1, days_diff):
                                missing = current.replace(day=current.day + j)
                                missing_dates.append(missing.strftime("%Y-%m-%d"))

                    # 輸出簽到記錄
                    for date in sorted_items:
                        output.append(f"  📆 {date} ✅")

                    # 輸出缺失記錄
                    if missing_dates:
                        output.append("")
                        output.append("【缺失記錄】")
                        for date in missing_dates:
                            output.append(f"  📆 {date} ❌")
                except:
                    # 如果日期解析失敗，直接輸出
                    for date in sorted_items:
                        output.append(f"  📆 {date} ✅")
            else:
                for date in sorted_items:
                    output.append(f"  📆 {date} ✅")
        else:
            output.append("【簽到記錄】")
            output.append("  📭 暫無簽到記錄")

        output.append("")

        # 使用統計
        output.append("【使用統計】")
        output.append(f"  📤 今日發送：{send_num}")
        output.append(f"  📥 今日使用：{used_num}")
        output.append(f"  💾 可用額度：{available_num}")

        output.append("")
        output.append("=" * 50)
        output.append(f" 報告時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 50)

        return "\n".join(output)

    except json.JSONDecodeError as e:
        return f"❌ JSON 解析錯誤：{str(e)}"
    except Exception as e:
        return f"❌ 格式化錯誤：{str(e)}"

def get_markdown_format(json_data, client_id=None):
    """
    將簽到狀態轉換為 Markdown 格式（適合 GitHub Action Summary）
    """
    try:
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        if data.get('status') != 200:
            cid = f" | client_id: `{client_id}`" if client_id is not None else ""
            return f"❌ 錯誤：API 回應異常 (狀態碼: {data.get('status')}){cid}"

        sign_data = data.get('data', {})
        sign_status = sign_data.get('SigninStatus', 0)
        sign_count = sign_data.get('signcount', 0)
        items = sign_data.get('items', [])

        status_text = "✅ 已簽到" if sign_status == 1 else "❌ 未簽到"

        # 建立 Markdown 表格
        markdown = []
        markdown.append("## 📊 簽到狀態報告")
        markdown.append("")
        markdown.append("| 項目 | 狀態 |")
        markdown.append("|------|------|")
        if client_id is not None:
            markdown.append(f"| 🆔 client_id | `{client_id}` |\n")
        markdown.append(f"| 🔐 簽到狀態 | {status_text} |\n")
        markdown.append(f"| 📊 連續簽到天數 | {sign_count} 天 |\n")

        if items:
            items_str = ", ".join(items)
            markdown.append(f"| 📆 簽到記錄 | {items_str} |\n")

            # 詳細記錄
            markdown.append("")
            markdown.append("### 📝 簽到明細\n")
            for date in sorted(items):
                markdown.append(f"- {date} ✅\n")
        else:
            markdown.append(f"| 📆 簽到記錄 | 暫無記錄 |")

        return "\n".join(markdown)

    except Exception as e:
        return f"❌ 格式化錯誤：{str(e)}"


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


# ======== 推送通知 ========

def send_msg_by_server(send_key, title, content):
    push_url = f'https://sctapi.ftqq.com/{send_key}.send'
    data = {
        'text': title,
        'desp': content
    }
    try:
        response = requests.post(push_url, data=data)
        return response.json()
    except RequestException:
        return None


def processAccount():
    tokenList = [token.strip() for token in MILWAUKEETOOL_TOKEN_LIST.split(',') if token.strip()]
    clientIdList = [id.strip() for id in MILWAUKEETOOL_CLIENT_ID.split(',') if id.strip()]

    # Mask first token for logs (avoid leaking full credentials)
    if tokenList:
        first = tokenList[0]
        token_show = (
            f"{first[:6]}...{first[-4:]}" if len(first) > 10 else "***"
        )
    else:
        token_show = "(empty)"

    print(f"      ├─ 方法: {GLOBAL_METHOD}")
    print(f"      ├─ ID: {clientIdList}")
    print(f"      └─ Token: {token_show}")

    if not tokenList or not clientIdList:
        msg = "缺少 token 或 client_id"
        print(f"      ❌ 结果: {msg}")
        FAILED_LOG.append(("config", msg))
        return False

    # 确保长度一致
    min_length = min(len(tokenList), len(clientIdList))
    tokenList = tokenList[:min_length]
    clientIdList = clientIdList[:min_length]

    print(f"🔧 共发现 {min_length} 个账号需要签到")
    print("   （Token 与 CLIENT_ID 须按逗号顺序一一对应：第1个Token↔第1个ID）")

    for idx, (token, client_id) in enumerate(zip(tokenList, clientIdList), 1):
        print(f"\n{'─' * 52}")
        print(f"📌 账号 {idx}/{min_length}  |  client_id: {client_id}")
        print(f"{'─' * 52}")
        signAndList(token, client_id, account_index=idx)


def signAndList(token, client_id, account_index=1):
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
        signStatus = resp_json.get("status")
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

            #--------
            print("\n📢 開始檢查簽到天數")
            delay = random.uniform(1.0, 2.5)
            print(f"      ⏳ 等待 {delay:.1f}s...")
            time.sleep(delay)
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "token": token,
                "client_id": client_id,
                "appkey": APPKEY,
                "format": FORMAT,
                "timestamp": timestamp_str,
                "platform": PLATFORM,
                "method": "get.signon.list"
            }
            sign_val = generate_sign(payload)
            payload["sign"] = sign_val
            response = requests.post(URL, headers=HEADERS, json=payload, timeout=40)
            resp_json = response.json()
            signResult = format_sign_status(resp_json, client_id=client_id)
            print(f"{signResult}")

            # Only Server 酱 when sign API returns 200. add.signon.item + 500 + 已签到: no push.
            if signStatus == 200:
                RESULT_LOG.append(signResult)
            elif (
                GLOBAL_METHOD == "add.signon.item"
                and signStatus == 500
                and ("已签到" in str(msg) or "已簽到" in str(msg))
            ):
                print("⏭️ add.signon.item 返回 500（已簽到），不發 Server 酱通知")
            else:
                print(f"⏭️ SendKey... 无更動获取，跳过通知 (status={signStatus})")
            return True
        else:
            api_status = resp_json.get("status")
            http_code = response.status_code
            print(
                f"      ⚠️ 结果: 失败 "
                f"(HTTP {http_code}, API status={api_status}, code={code}) | {msg}"
            )
            # 失败时强制打印完整返回
            print(f"      └─ 完整返回:\n{json.dumps(resp_json, ensure_ascii=False, indent=4)}")

            if api_status == 401 or http_code == 401 or "未授权" in str(msg) or "授权" in str(
                msg
            ) and "过期" in str(msg):
                print(
                    "      💡 该账号 Token 已过期，或与当前 client_id 不是同一组（顺序对错也会 401）。"
                    "请到 Milwaukee 微信小程序重新登录，抓包/复制新 Token，并更新环境变量里"
                    f"第 {account_index} 个 Token（与第 {account_index} 个 client_id 对齐）。"
                )

            # 记录失败信息用于通知
            short_msg = msg if len(msg) < 50 else msg[:47] + "..."
            FAILED_LOG.append(
                (client_id, f"{short_msg} (HTTP:{http_code}, API:{api_status}, code:{code})")
            )
            return False

    except Exception as e:
        err_msg = str(e)
        print(f"      ❌ 结果: 网络/系统错误 - {err_msg}")
        FAILED_LOG.append((client_id, f"网络错误: {err_msg}"))
        return False

def sendNotification():
    if not RESULT_LOG:
        print("📤 暂无签到汇总内容，跳过 Server 酱通知。")
        return

    keys = [k.strip() for k in SEND_KEY_LIST.split(",") if k.strip()]
    if not keys:
        print("📤 未配置 SEND_KEY_LIST，跳过 Server 酱通知。")
        return

    content = "\n\n".join(RESULT_LOG)
    print(f"📤 检测到有簽到，准备发送通知... (keys: {len(keys)} 个)")

    for send_key in keys:
        response = send_msg_by_server(send_key, "milwaukeetool签到汇总", content)
        if response and response.get("code") == 0:
            print(
                f"✅ 通知发送成功！(key ...{send_key[-4:]}) 消息ID: "
                f"{response.get('data', {}).get('pushid', '')}"
            )
        else:
            error_msg = response.get("message") if response else "未知错误"
            print(f"❌ 通知发送失败！(key ...{send_key[-4:]}) 错误: {error_msg}")

def main():
    print("=" * 60)
    print(f"🚀 批量签到启动 | 模式: {GLOBAL_METHOD}")
    print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_count = 0
    failed_list = []  # 存储 (名字, 原因)

    processAccount()
    sendNotification()

    # 汇总
    print("\n" + "=" * 60)
    print(f"🏁 任务结束")
    print("=" * 60)

    # 如果有失败，发送通知
    if len(FAILED_LOG) > 0:
        print("\n失敗。")
    else:
        print("\n🎉 全部成功，无需发送通知。")


if __name__ == "__main__":
    main()
