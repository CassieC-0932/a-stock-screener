# 消息推送配置指南

本系统支持四个推送渠道：**飞书、钉钉、邮件、Server酱（微信）**，可同时启用多个。  
推送由 `scripts/notifier.py` 统一调度，`scripts/scheduler.py` 负责每个交易日 15:35 自动触发。

---

## 快速开始

1. 复制配置文件

```bash
cp config.example.py config.py
```

2. 在 `config.py` 中找到 `notify` 字段，将对应渠道的 `"enabled"` 改为 `True` 并填入凭据。

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 启动调度器

```bash
# 前台运行（Ctrl+C 停止）
python3 scripts/scheduler.py

# 后台常驻运行
nohup python3 scripts/scheduler.py > logs/scheduler.log 2>&1 &
```

---

## 飞书机器人

### 第一步：创建机器人

1. 打开飞书，进入目标群组
2. 点击右上角 **群设置** → **机器人** → **添加机器人**
3. 选择 **自定义机器人**，填写名称（如"选股助手"）
4. 安全设置选择 **签名校验**（推荐），记录生成的 **Webhook URL** 和 **密钥**

> 如果不启用签名校验，`secret` 留空即可，但建议至少开启 IP 白名单。

### 第二步：填写配置

```python
"feishu": {
    "enabled": True,
    "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "secret": "your_signing_secret",   # 不启用签名时填 ""
},
```

### 效果预览

推送内容为蓝色标题卡片，正文支持 Markdown 格式（**加粗**、`代码`、列表等）。

---

## 钉钉机器人

### 第一步：创建机器人

1. 打开钉钉，进入目标群组
2. 点击右上角 **…** → **智能群助手** → **添加机器人** → **自定义**
3. 安全设置选择 **加签**，记录生成的 **Webhook URL** 和 **加签密钥**

### 第二步：填写配置

```python
"dingtalk": {
    "enabled": True,
    "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "secret": "SECxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
},
```

> `secret` 即"加签"密钥，以 `SEC` 开头。若安全模式选择"自定义关键词"而非加签，则 `secret` 填 `""` 并确保报告标题包含你设定的关键词。

### 效果预览

推送内容为 Markdown 消息，标题加粗显示，群内所有成员可见。

---

## 邮件（SMTP）

### 常用邮件服务商配置

| 服务商 | smtp_host | smtp_port | 说明 |
|--------|-----------|-----------|------|
| QQ 邮箱 | `smtp.qq.com` | `465` | 密码为**授权码**，非登录密码 |
| 163 邮箱 | `smtp.163.com` | `465` | 密码为**授权码** |
| Gmail | `smtp.gmail.com` | `587` | 需开启两步验证并生成应用专用密码 |
| 企业邮箱 | 询问管理员 | `465`/`587` | — |

### 获取授权码（以 QQ 邮箱为例）

1. 登录 QQ 邮箱网页版 → **设置** → **账户**
2. 找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务**
3. 开启 **SMTP 服务**，按提示发送短信后获得 16 位授权码

### 填写配置

```python
"email": {
    "enabled": True,
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "username": "your@qq.com",
    "password": "your_auth_code",       # 16 位授权码，非 QQ 密码
    "to_addrs": ["your@qq.com", "another@example.com"],  # 支持多个收件人
},
```

---

## Server酱（微信推送）

Server酱是最简单的微信推送方案，无需企业微信，个人微信即可接收。

### 第一步：注册并绑定微信

1. 访问 [https://sct.ftqq.com](https://sct.ftqq.com)
2. 用 GitHub 账号登录
3. 按提示扫码绑定微信（关注"方糖"公众号）
4. 在控制台复制你的 **SendKey**（格式为 `SCT...`）

> 免费版每天限推 5 条，日常使用足够；如需更多可升级。

### 第二步：填写配置

```python
"serverchan": {
    "enabled": True,
    "sendkey": "SCTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
},
```

### 效果预览

微信会收到"方糖"公众号的模板消息，点击可查看完整报告。

---

## 同时启用多个渠道

将需要的渠道都设为 `"enabled": True`，系统会按顺序逐一推送，任一失败不影响其他渠道。

```python
"notify": {
    "feishu":     {"enabled": True,  "webhook": "...", "secret": "..."},
    "dingtalk":   {"enabled": False, "webhook": "...", "secret": "..."},
    "email":      {"enabled": True,  "smtp_host": "smtp.qq.com", ...},
    "serverchan": {"enabled": False, "sendkey": "..."},
},
```

---

## 手动测试推送

不需要等到 15:35，随时可以手动验证配置是否正确：

```bash
cd scripts
python3 -c "
from notifier import notify
notify('测试标题', '这是一条来自A股选股系统的测试消息。\n**配置成功！**')
"
```

执行后在对应渠道收到消息即表示配置正确。

---

## 调度器管理

```bash
# 查看调度器是否在运行
ps aux | grep scheduler.py

# 停止后台调度器
kill $(pgrep -f scheduler.py)

# 查看运行日志
tail -f logs/scheduler.log
```

调度器会在每个 **交易日** 的 **15:35** 自动运行选股并推送。节假日、周末会自动跳过，无需手动干预。

---

## 常见问题

**Q：钉钉报错 `sign not match`**  
A：服务器时间与钉钉服务器时差超过 1 小时会导致签名失败。检查系统时间是否准确，可执行 `date` 命令查看。

**Q：QQ 邮箱发送失败 `Authentication failed`**  
A：`password` 填的是授权码，不是 QQ 密码。授权码为 16 位英文字母，在邮箱设置中生成。

**Q：飞书收到消息但显示异常**  
A：正文使用飞书 Markdown（`lark_md`）语法，`**加粗**`、`> 引用`、`- 列表` 均支持，但部分标准 Markdown 语法（如 `###` 标题）在飞书卡片中不生效。

**Q：Server酱收不到微信消息**  
A：确认已关注"方糖"公众号且未取消关注；免费版每天上限 5 条，超出后当天不再推送。
