---
name: 手机朋友圈
description: 将内容发布到微信朋友圈。当用户说"发朋友圈"、"发布到朋友圈"、"发个朋友圈"、"发一条朋友圈"时触发。支持公开、部分人不可见、仅自己可见三种模式。
---

# 手机朋友圈

将指定内容发布到微信朋友圈。

## 流程

### 1. 确认内容和发布方式

向用户确认：
- 文案内容是否满意
- 发布方式：公开 / 部分人不可见 / 仅自己可见

### 2. 执行发布

```bash
cd "<skill目录>/scripts"

# 公开发布
python wechat_moments.py post "内容"

# 部分人不可见
python wechat_moments.py post "内容" --group

# 仅自己可见
python wechat_moments.py private "内容"
```

### 3. 报告结果

告知用户发布是否成功。
