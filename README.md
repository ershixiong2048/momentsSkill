# 手机朋友圈 - Claude Code Skill

一个用于自动发布微信朋友圈的 Claude Code Skill。 欢迎到 https://mp.weixin.qq.com/s/WSbQMuWA0Sz3WL-VzoN3PQ  看完整教程

## 功能

- 支持三种发布模式：公开、部分人可见、私密（仅自己可见）
- 自动处理长内容滚动
- 自动清空输入框缓存内容
- 支持标签分组管理

## 安装

### 方式一：

打开ClaudeCode/Codex等Agent，发送以下内容

> 帮我安装这个skill  [github地址] 

### 方式二：

将此 skill 目录复制到你的项目的 `.claude/skills/` 目录下：

```
your-project/
└── .claude/
    └── skills/
        └── weChatMoments/
            ├── SKILL.md
            ├── README.md
            └── scripts/
                ├── wechat_moments.py
                └── config.json
```

## 前置条件

- Python 3.x
- ADB 已安装并添加到 PATH
- 手机已通过 USB 连接并开启 USB 调试
- 微信已安装并登录

### Python 依赖

```bash
pip install pyperclip uiautomator2
```

## 使用方式

### 方式一：自动触发

当你说以下关键词时，Claude 会自动调用此 skill：

- 发朋友圈
- 发布到朋友圈
- 发个朋友圈
- 发一条朋友圈

### 方式二：手动调用

```bash
cd .claude/skills/手机朋友圈/scripts

# 公开发布
python wechat_moments.py post "你要发布的内容"

# 部分人不可见
python wechat_moments.py post "你要发布的内容" --group

# 私密（仅自己可见）
python wechat_moments.py private "你要发布的内容"
```

## 配置文件

配置文件位于 `scripts/config.json`：

```json
{
  "visibility": {
    "mode": "hide_from",
    "group_name": "常用不可见人群"
  },
  "delay_between_posts": 5,
  "device_resolution": null
}
```

### 配置项说明

| 配置项                  | 类型   | 说明                                                      |
| ----------------------- | ------ | --------------------------------------------------------- |
| `visibility.mode`       | string | 可见性模式，目前支持 `hide_from`（不给谁看）              |
| `visibility.group_name` | string | 标签名称，对应微信中的分组标签                            |
| `delay_between_posts`   | int    | 多条发布时的间隔时间（秒）                                |
| `device_resolution`     | int[]  | 设备分辨率，默认为 `[1080, 1920]`，设为 `null` 则自动检测 |

### 如何配置标签分组

1. 在微信中创建标签：通讯录 → 标签 → 新建标签
2. 将不想让其看到朋友圈的人添加到该标签
3. 将标签名称填入 `config.json` 的 `visibility.group_name`

## 目录结构

```
手机朋友圈/
├── SKILL.md              # Skill 定义文件
├── README.md             # 本说明文件
└── scripts/
    ├── wechat_moments.py # 发布脚本
    └── config.json       # 配置文件
```

## 工作原理

1. 通过 ADB 连接手机
2. 使用 `uiautomator2` 操作微信界面
3. 自动执行：打开微信 → 发现 → 朋友圈 → 长按相机 → 输入内容 → 设置可见性 → 发表

## 常见问题

**Q: 提示找不到 ADB？**
A: 确保 ADB 已安装并添加到系统 PATH，或在脚本中指定 ADB 路径。

**Q: 内容没有输入成功？**
A: 确保手机已连接，微信已登录，且输入法支持中文输入。

**Q: 找不到"谁可以看"按钮？**
A: 脚本会自动滚动页面，确保按钮可见。

## License

MIT
