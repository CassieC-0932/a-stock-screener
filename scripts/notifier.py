# -*- coding: utf-8 -*-
"""
A股选股系统 - 消息推送模块

支持三个推送渠道（可同时启用多个）：
  1. 钉钉机器人 Webhook（加签安全模式）
  2. 邮件（SMTP）
  3. Server酱（微信推送，https://sct.ftqq.com）

在 config.py 的 NOTIFY 字段中配置启用哪些渠道。
"""

import hashlib
import hmac
import base64
import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _load_notify_config() -> dict:
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from config import CONFIG  # type: ignore
        return CONFIG.get('notify', {})
    except ImportError:
        return {}


# ── 钉钉 ──────────────────────────────────────────────────────────────────────

def _dingtalk_sign(secret: str) -> tuple:
    """生成钉钉加签串，返回 (timestamp, sign)"""
    ts = str(round(time.time() * 1000))
    string_to_sign = f"{ts}\n{secret}"
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    sign = quote(base64.b64encode(hmac_code), safe='')
    return ts, sign


def send_dingtalk(title: str, content: str, webhook: str, secret: Optional[str] = None) -> bool:
    """发送钉钉机器人消息（Markdown 格式）"""
    url = webhook
    if secret:
        ts, sign = _dingtalk_sign(secret)
        url = f"{webhook}&timestamp={ts}&sign={sign}"

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get('errcode') == 0:
            logger.info("钉钉推送成功")
            return True
        logger.warning("钉钉推送失败: %s", result)
    except Exception as e:
        logger.error("钉钉推送异常: %s", e)
    return False


# ── 邮件 ──────────────────────────────────────────────────────────────────────

def send_email(subject: str, content: str, smtp_host: str, smtp_port: int,
               username: str, password: str, to_addrs: list) -> bool:
    """发送邮件（支持 SSL/TLS，内容为纯文本）"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = username
        msg['To'] = ', '.join(to_addrs)
        msg.attach(MIMEText(content, 'plain', 'utf-8'))

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(username, password)
        server.sendmail(username, to_addrs, msg.as_string())
        server.quit()
        logger.info("邮件推送成功 -> %s", to_addrs)
        return True
    except Exception as e:
        logger.error("邮件推送失败: %s", e)
    return False


# ── Server酱（微信）────────────────────────────────────────────────────────────

def send_serverchan(title: str, content: str, sendkey: str) -> bool:
    """通过 Server酱 推送到微信（https://sct.ftqq.com）"""
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    try:
        resp = requests.post(url, data={'title': title, 'desp': content}, timeout=10)
        result = resp.json()
        if result.get('code') == 0:
            logger.info("Server酱推送成功")
            return True
        logger.warning("Server酱推送失败: %s", result)
    except Exception as e:
        logger.error("Server酱推送异常: %s", e)
    return False


# ── 飞书 ──────────────────────────────────────────────────────────────────────

def send_feishu(title: str, content: str, webhook: str, secret: Optional[str] = None) -> bool:
    """
    发送飞书机器人消息（富文本卡片格式）。
    webhook: 飞书群机器人的 Webhook URL
    secret:  开启签名校验时的密钥（可选）
    """
    url = webhook
    headers = {'Content-Type': 'application/json; charset=utf-8'}

    if secret:
        ts = str(int(time.time()))
        sign_str = f"{ts}\n{secret}"
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        payload = {
            "timestamp": ts,
            "sign": sign,
            "msg_type": "interactive",
            "card": {
                "elements": [{"tag": "div", "text": {"content": content, "tag": "lark_md"}}],
                "header": {"title": {"content": title, "tag": "plain_text"}, "template": "blue"},
            },
        }
    else:
        payload = {
            "msg_type": "interactive",
            "card": {
                "elements": [{"tag": "div", "text": {"content": content, "tag": "lark_md"}}],
                "header": {"title": {"content": title, "tag": "plain_text"}, "template": "blue"},
            },
        }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        result = resp.json()
        if result.get('code') == 0 or result.get('StatusCode') == 0:
            logger.info("飞书推送成功")
            return True
        logger.warning("飞书推送失败: %s", result)
    except Exception as e:
        logger.error("飞书推送异常: %s", e)
    return False


# ── 统一入口 ──────────────────────────────────────────────────────────────────

def notify(title: str, content: str) -> None:
    """
    根据 config.py 中的 NOTIFY 配置，向所有已启用渠道推送消息。
    任一渠道失败不影响其他渠道。
    """
    cfg = _load_notify_config()
    if not cfg:
        logger.debug("未配置 NOTIFY，跳过推送")
        return

    # 钉钉
    dd = cfg.get('dingtalk', {})
    if dd.get('enabled') and dd.get('webhook'):
        send_dingtalk(title, content, dd['webhook'], dd.get('secret'))

    # 邮件
    mail = cfg.get('email', {})
    if mail.get('enabled') and mail.get('smtp_host'):
        send_email(
            subject=title,
            content=content,
            smtp_host=mail['smtp_host'],
            smtp_port=int(mail.get('smtp_port', 465)),
            username=mail['username'],
            password=mail['password'],
            to_addrs=mail.get('to_addrs', [mail['username']]),
        )

    # Server酱
    sc = cfg.get('serverchan', {})
    if sc.get('enabled') and sc.get('sendkey'):
        send_serverchan(title, content, sc['sendkey'])

    # 飞书
    fs = cfg.get('feishu', {})
    if fs.get('enabled') and fs.get('webhook'):
        send_feishu(title, content, fs['webhook'], fs.get('secret'))
