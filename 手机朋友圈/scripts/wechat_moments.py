#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信朋友圈自动发布脚本（带步骤校验和错误恢复）"""

import subprocess
import time
import re
import sys
import json
import os
import pyperclip
import xml.etree.ElementTree as ET

# 设置控制台编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ─────────────── UI 交互层 ───────────────

def tap(x, y):
    """点击屏幕坐标"""
    subprocess.run(["adb", "shell", f"input tap {x} {y}"], capture_output=True)
    time.sleep(0.3)

def long_press(x, y, duration_ms=1000):
    """长按屏幕坐标"""
    subprocess.run(["adb", "shell", f"input swipe {x} {y} {x} {y} {duration_ms}"], capture_output=True)
    time.sleep(0.3)

def press_back():
    subprocess.run(["adb", "shell", "input keyevent 4"], capture_output=True)
    time.sleep(0.3)

def set_android_clipboard(text):
    """通过写入临时文件 + input 模拟设置 Android 剪贴板"""
    # 把文本写入手机临时文件
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["adb", "shell", f'echo -n "{escaped}" > /data/local/tmp/_clip.txt'], capture_output=True)
    # 用 am 命令触发读取文件到剪贴板（需要 Clipper 类似工具）
    # 最可靠方案：直接用 input 模拟输入
    time.sleep(0.2)


def set_clipboard(text):
    """设置剪贴板"""
    pyperclip.copy(text)
    time.sleep(0.1)

def adb_paste():
    """ADB粘贴"""
    subprocess.run(["adb", "shell", "input keyevent 279"], capture_output=True)
    time.sleep(0.3)

def adb_keyboard_input(text):
    """用 ADB 键盘直接输入文字（不依赖剪贴板）"""
    # 切换到 ADB 键盘
    subprocess.run(["adb", "shell", "ime", "set", "com.github.uiautomator/.AdbKeyboard"],
                   capture_output=True)
    time.sleep(0.3)
    # 广播发送文字到当前焦点输入框
    subprocess.run(["adb", "shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT",
                    "--es", "msg", text], capture_output=True)
    time.sleep(0.5)

def adb_input_chinese(text):
    """通过 ADB 广播输入中文（需要 ADBKeyBoard 输入法）"""
    # 先切换到 ADBKeyBoard
    subprocess.run(["adb", "shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
                   capture_output=True)
    time.sleep(0.3)
    # 广播发送文字
    subprocess.run(["adb", "shell", "am", "broadcast", "-a", "ADB_INPUT_TEXT",
                    "--es", "msg", text], capture_output=True)
    time.sleep(0.5)
    # 切回原输入法
    subprocess.run(["adb", "shell", "ime", "set", "com.sohu.inputmethod.sogou/.SogouIME"],
                   capture_output=True)
    time.sleep(0.3)

def adb_type_text(text):
    """通过剪贴板输入中文"""
    set_clipboard(text)
    adb_paste()

def adb_send_keys(text):
    """通过 uiautomator2 直接输入文字（不依赖剪贴板）"""
    try:
        import uiautomator2 as u2
        d = u2.connect()
        d.send_keys(text)
        time.sleep(0.5)
        # 验证：检查UI中是否包含输入的文字
        xml = d.dump_hierarchy()
        if text[:10] in xml:  # 检查前10个字符
            return True
        else:
            print(f"[WARN] send_keys 执行但内容未出现在UI中")
            return False
    except Exception as e:
        print(f"[WARN] send_keys 异常: {e}")
        return False

def adb_pure_type(text):
    """纯英文/数字用adb shell input text"""
    subprocess.run(["adb", "shell", f"input text '{text}'"], capture_output=True)
    time.sleep(0.3)

def dump_ui():
    """通过uiautomator2获取当前页面UI"""
    try:
        import uiautomator2 as u2
        d = u2.connect()
        xml_str = d.dump_hierarchy()
        return xml_str
    except Exception as e:
        print(f"uiautomator2 error: {e}")
        # 备用方案：用adb
        result = subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui.xml"],
                                capture_output=True, text=True)
        result = subprocess.run(["adb", "shell", "cat", "/sdcard/ui.xml"],
                                capture_output=True, text=True)
        return result.stdout

def find_by_text(xml_str, text):
    """通过文本查找元素坐标，返回中心坐标或None"""
    try:
        root = ET.fromstring(xml_str)
        for elem in root.iter('node'):
            txt = elem.get('text', '')
            if text in txt:
                bounds = elem.get('bounds', '')
                match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    return ((x1 + x2) // 2, (y1 + y2) // 2)
    except:
        pass
    return None

def find_by_text_contains(xml_str, text):
    """通过包含文本查找元素"""
    return find_by_text(xml_str, text)

def find_by_text_exact(xml_str, text):
    """通过精确文本查找"""
    try:
        root = ET.fromstring(xml_str)
        for elem in root.iter('node'):
            txt = elem.get('text', '')
            if txt == text:
                bounds = elem.get('bounds', '')
                match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    return ((x1 + x2) // 2, (y1 + y2) // 2)
    except:
        pass
    return None

def find_by_content_desc(xml_str, desc):
    """通过contentDescription查找元素"""
    try:
        root = ET.fromstring(xml_str)
        for elem in root.iter('node'):
            cd = elem.get('content-desc', '')
            if desc in cd:
                bounds = elem.get('bounds', '')
                match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                if match:
                    x1, y1, x2, y2 = map(int, match.groups())
                    return ((x1 + x2) // 2, (y1 + y2) // 2)
    except:
        pass
    return None

def get_current_package():
    """获取当前前台应用包名"""
    result = subprocess.run(["adb", "shell", "dumpsys activity activities"],
                            capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'mResumedActivity' in line or 'topResumedActivity' in line:
            match = re.search(r'([a-zA-Z0-9.]+/[a-zA-Z0-9.]+)', line)
            if match:
                return match.group(1).split('/')[0]
    return ""

# ─────────────── 步骤验证器 ───────────────

class StepValidator:
    """步骤验证和错误恢复"""

    @staticmethod
    def wait_for_element(text, timeout=5, check_interval=0.5):
        """等待元素出现"""
        for _ in range(int(timeout / check_interval)):
            xml = dump_ui()
            if find_by_text(xml, text):
                return True
            time.sleep(check_interval)
        return False

    @staticmethod
    def ensure_on_wechat_home(max_retries=3):
        """确保在微信首页"""
        for i in range(max_retries):
            pkg = get_current_package()
            if pkg == "com.tencent.mm":
                xml = dump_ui()
                # 检查是否在微信首页（有"微信"tab）
                if find_by_text(xml, "微信") or find_by_text(xml, "通讯录") or find_by_text(xml, "发现"):
                    return True
            # 不在微信首页，按返回键
            press_back()
            time.sleep(0.5)
        return False

    @staticmethod
    def ensure_on_discover_page(max_retries=3):
        """确保在发现页面"""
        for i in range(max_retries):
            xml = dump_ui()
            # 检查是否在发现页面（有朋友圈、直播、看一看等）
            if find_by_text(xml, "朋友圈") and (find_by_text(xml, "直播") or find_by_text(xml, "视频号")):
                return True
            # 如果在微信首页，点击发现
            pos = find_by_text(xml, "发现")
            if pos:
                tap(pos[0], pos[1])
                time.sleep(0.5)
                continue
            # 如果在其他地方，按返回
            press_back()
            time.sleep(0.3)
        return False

    @staticmethod
    def ensure_on_moments_page(max_retries=3):
        """确保在朋友圈页面"""
        for i in range(max_retries):
            xml = dump_ui()
            # 朋友圈页面应该有相机图标
            if find_by_content_desc(xml, "拍照") or find_by_text(xml, "发现"):
                return True
            time.sleep(0.3)
        return False

    @staticmethod
    def ensure_on_publish_page(max_retries=3):
        """确保在发布页面"""
        for i in range(max_retries):
            xml = dump_ui()
            # 发布页面应该有"发表"按钮或"完成"按钮
            if find_by_text(xml, "发表") or find_by_text(xml, "完成"):
                return True
            time.sleep(0.3)
        return False

    @staticmethod
    def ensure_visibility_dialog_open(max_retries=3):
        """确保谁可以看弹窗打开"""
        for i in range(max_retries):
            xml = dump_ui()
            if find_by_text(xml, "不给谁看") and find_by_text(xml, "选择标签"):
                return True
            time.sleep(0.3)
        return False

# ─────────────── 核心功能 ───────────────

def step1_open_wechat():
    """打开微信"""
    print("[1/12] 打开微信...", end=" ", flush=True)
    # 先强杀微信，确保从干净状态开始
    subprocess.run(["adb", "shell", "am", "force-stop", "com.tencent.mm"],
                   capture_output=True)
    time.sleep(1)
    subprocess.run(["adb", "shell", "am", "start", "-n", "com.tencent.mm/.ui.LauncherUI"],
                   capture_output=True)
    time.sleep(2)

    # 验证：微信已打开
    pkg = get_current_package()
    if pkg != "com.tencent.mm":
        print("[FAIL] 微信未打开")
        return False

    # 验证：在微信首页或发现页
    for i in range(5):
        xml = dump_ui()
        # 检查是否在微信首页或发现页
        if find_by_text(xml, "微信") and find_by_text(xml, "通讯录") and find_by_text(xml, "发现"):
            print("[OK]")
            return True
        # 按返回键回到首页
        press_back()
        time.sleep(0.5)

    print("[FAIL] 未到达微信首页")
    return False

def step2_click_discover():
    """点击发现"""
    print("[2/12] 点击发现...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text(xml, "发现")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            # 验证：到达发现页面
            if StepValidator.ensure_on_discover_page(2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未找到'发现'")
    return False

def step3_click_moments():
    """点击朋友圈"""
    print("[3/12] 点击朋友圈...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text(xml, "朋友圈")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(1)
            # 验证：进入朋友圈页面
            if StepValidator.ensure_on_moments_page(2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未找到'朋友圈'")
    return False

def step4_long_press_camera():
    """长按相机图标进入纯文字发布页面"""
    print("[4/12] 长按相机...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        # 找到相机图标
        pos = find_by_content_desc(xml, "拍照")
        if pos:
            # 长按相机图标（进入纯文字发布页面）
            long_press(pos[0], pos[1], 1500)
            time.sleep(1)

            # 处理可能的草稿弹窗
            draft_xml = dump_ui()
            if find_by_text(draft_xml, "保留当前内容"):
                discard_pos = find_by_text(draft_xml, "不保留")
                if discard_pos:
                    tap(discard_pos[0], discard_pos[1])
                    time.sleep(0.5)

            # 验证：进入发布页面（有"谁可以看"选项）
            if StepValidator.ensure_on_publish_page(2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未进入发布页面")
    return False

def step5_paste_content(content):
    """粘贴内容"""
    print("[5/12] 粘贴内容...", end=" ", flush=True)

    # 点击输入框（"这一刻的想法..."）
    xml = dump_ui()
    pos = find_by_text(xml, "这一刻的想法...")
    if pos:
        tap(pos[0], pos[1])
        time.sleep(0.3)

    # 清空输入框（可能有上次缓存的内容）
    # 全选再删除
    subprocess.run(["adb", "shell", "input", "keyevent", "29", "--longpress"], capture_output=True)  # Ctrl+A
    time.sleep(0.2)
    subprocess.run(["adb", "shell", "input", "keyevent", "67"], capture_output=True)  # Delete
    time.sleep(0.2)

    # 用 uiautomator2 输入内容（比 ADB 广播更可靠）
    if not adb_send_keys(content):
        # 备用方案：用剪贴板粘贴
        print("[WARN] send_keys失败，尝试剪贴板...", end=" ", flush=True)
        set_clipboard(content)
        time.sleep(0.2)
        # 长按输入框触发粘贴菜单
        if pos:
            long_press(pos[0], pos[1], 1000)
            time.sleep(0.5)
            # 点击粘贴
            paste_pos = find_by_text(dump_ui(), "粘贴")
            if paste_pos:
                tap(paste_pos[0], paste_pos[1])
                time.sleep(0.5)
    time.sleep(0.5)

    # 验证：内容已粘贴（输入法会自动关闭，不需要按返回键）
    if StepValidator.ensure_on_publish_page(2):
        print("[OK]")
        return True

    print("[FAIL] 粘贴失败")
    return False

def step6_paste_content(content):
    """粘贴内容"""
    print("[6/13] 粘贴内容...", end=" ", flush=True)

    # 先设置剪贴板
    set_clipboard(content)

    # 点击输入框
    xml = dump_ui()
    # 尝试找输入框
    pos = find_by_text(xml, "这一刻的想法...")
    if not pos:
        # 尝试其他可能的文本
        pos = find_by_text(xml, "添加文字")
    if pos:
        tap(pos[0], pos[1])
        time.sleep(0.3)

    # 粘贴
    adb_paste()
    time.sleep(0.5)

    # 验证：内容已粘贴
    if StepValidator.ensure_on_publish_page(2):
        print("[OK]")
        return True

    print("[FAIL] 粘贴失败")
    return False

def step7_click_who_can_see():
    """点击谁可以看"""
    print("[6/12] 点击谁可以看...", end=" ", flush=True)

    # 粘贴内容后固定向上滚动一下，确保"谁可以看"按钮可见
    subprocess.run(["adb", "shell", "input", "swipe", "540", "1800", "540", "800", "300"], capture_output=True)
    time.sleep(0.5)

    for attempt in range(3):
        xml = dump_ui()
        # 检查是否已经在"谁可以看"的选项列表页面
        if find_by_text(xml, "不给谁看") and find_by_text(xml, "部分可见"):
            print("[OK] (已在选项页面)")
            return True
        # 点击"谁可以看"按钮
        pos = find_by_text(xml, "谁可以看")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            # 验证：弹窗打开
            if StepValidator.ensure_visibility_dialog_open(2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未找到'谁可以看'")
    return False

def step8_click_hide_from():
    """点击不给谁看"""
    print("[7/12] 点击不给谁看...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text(xml, "不给谁看")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            # 验证：进入选择页面
            if StepValidator.wait_for_element("选择标签", 2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未找到'不给谁看'")
    return False

def step9_click_select_tag():
    """点击选择标签"""
    print("[8/12] 点击选择标签...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text(xml, "选择标签")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            # 验证：进入搜索页面
            if StepValidator.wait_for_element("搜索", 2):
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 未找到'选择标签'")
    return False

def step10_search_tag(tag_name):
    """搜索标签"""
    print(f"[9/12] 搜索标签'{tag_name}'...", end=" ", flush=True)

    # 点击搜索框
    xml = dump_ui()
    pos = find_by_text(xml, "搜索")
    if pos:
        tap(pos[0], pos[1])
        time.sleep(0.3)

    # 清空搜索框：先全选再删除
    subprocess.run(["adb", "shell", "input", "keyevent", "29", "--longpress"], capture_output=True)
    time.sleep(0.3)
    subprocess.run(["adb", "shell", "input", "keyevent", "67"], capture_output=True)
    time.sleep(0.2)
    subprocess.run(["adb", "shell", "input", "keyevent", "67"], capture_output=True)
    time.sleep(0.2)

    # 确保搜索框有焦点
    xml2 = dump_ui()
    search_pos = find_by_text(xml2, "搜索")
    if search_pos:
        tap(search_pos[0], search_pos[1])
        time.sleep(0.3)

    # 用 uiautomator2 输入标签名（比 ADB 广播更可靠）
    adb_send_keys(tag_name)
    time.sleep(1)

    # 调试：保存搜索结果页面 UI
    debug_xml = dump_ui()
    with open('debug_tag_search.xml', 'w', encoding='utf-8') as f:
        f.write(debug_xml)

    # 验证：搜索结果出现
    if StepValidator.wait_for_element(tag_name, 2):
        print("[OK]")
        return True

    print("[FAIL] 未找到标签")
    return False

def step11_select_tag(tag_name):
    """选择标签"""
    print(f"[10/12] 选择标签'{tag_name}'...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        # 查找所有包含 tag_name 的元素，跳过搜索框（EditText），点搜索结果
        try:
            root = ET.fromstring(xml)
            pos = None
            for elem in root.iter('node'):
                txt = elem.get('text', '')
                cls = elem.get('class', '')
                if tag_name in txt and 'EditText' not in cls:
                    bounds = elem.get('bounds', '')
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        pos = ((x1 + x2) // 2, (y1 + y2) // 2)
                        break
            if pos:
                tap(pos[0], pos[1])
                time.sleep(1)
                # 验证：选中状态（选择/确认按钮或已勾选）
                if StepValidator.wait_for_element("选择", 3) or StepValidator.wait_for_element("确认", 3):
                    print("[OK]")
                    return True
                xml2 = dump_ui()
                if "已选" in xml2 or "✓" in xml2:
                    print("[OK]")
                    return True
        except:
            pass
        time.sleep(0.5)

    print("[FAIL] 未选择到标签")
    return False

def step12_confirm():
    """确认选择"""
    print("[11/12] 确认选择...", end=" ", flush=True)

    for attempt in range(3):
        xml = dump_ui()
        # 找按钮类型的元素（避免匹配到页面标题"选择标签"）
        try:
            root = ET.fromstring(xml)
            pos = None
            for elem in root.iter('node'):
                txt = elem.get('text', '')
                cls = elem.get('class', '')
                if ('确认' in txt or '确定' in txt or '选择' in txt) and 'Button' in cls:
                    bounds = elem.get('bounds', '')
                    match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        pos = ((x1 + x2) // 2, (y1 + y2) // 2)
                        break
            if pos:
                tap(pos[0], pos[1])
                time.sleep(0.5)
                # 验证：返回发布页面
                if StepValidator.ensure_on_publish_page(2):
                    print("[OK]")
                    return True
        except:
            pass
        time.sleep(0.3)

    print("[FAIL] 未确认成功")
    return False

def step13_click_publish():
    """点击发表"""
    print("[12/12] 点击发表...", end=" ", flush=True)

    # 先检查是否在"谁可以看"页面，如果是先点"完成"
    xml = dump_ui()
    if find_by_text_exact(xml, "完成"):
        pos = find_by_text_exact(xml, "完成")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(1)

    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text_exact(xml, "发表")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(1)
            # 验证：发布成功（回到朋友圈页面或首页）
            pkg = get_current_package()
            if pkg == "com.tencent.mm":
                print("[OK]")
                return True
        time.sleep(0.3)

    print("[FAIL] 发布失败")
    return False

def post_moments(content, group_name=None):
    """发布朋友圈主流程"""
    print("=== 开始发布朋友圈 ===")
    print(f"内容长度: {len(content)} 字")
    if group_name:
        print(f"分组: 不给'{group_name}'看")
    print()

    # 步骤1：打开微信
    if not step1_open_wechat():
        return False

    # 步骤2：点击发现
    if not step2_click_discover():
        return False

    # 步骤3：点击朋友圈
    if not step3_click_moments():
        return False

    # 步骤4：长按相机（进入纯文字发布页面）
    if not step4_long_press_camera():
        return False

    # 步骤5：粘贴内容
    if not step5_paste_content(content):
        return False

    # 步骤7-12：分组设置（如果需要）
    if group_name:
        if not step7_click_who_can_see():
            return False
        if not step8_click_hide_from():
            return False
        if not step9_click_select_tag():
            return False
        if not step10_search_tag(group_name):
            return False
        if not step11_select_tag(group_name):
            return False
        if not step12_confirm():
            return False

    # 步骤13：点击发表
    if not step13_click_publish():
        return False

    print("\n=== 发布成功 ===")
    return True


def step_click_private():
    """点击私密（仅自己可见）并确认"""
    print("[7/8] 点击'私密'...", end=" ", flush=True)

    # 先点击"私密"
    clicked = False
    for attempt in range(5):
        time.sleep(0.5)
        xml = dump_ui()
        pos = find_by_text(xml, "私密")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            clicked = True
            break
        time.sleep(0.3)

    if not clicked:
        print("[FAIL] 未找到'私密'选项")
        return False

    # 点击"完成"确认
    xml = dump_ui()
    pos = find_by_text(xml, "完成")
    if pos:
        tap(pos[0], pos[1])
        time.sleep(0.8)

    # 验证：返回发布页面
    if StepValidator.wait_for_element("发表", 3):
        print("[OK]")
        return True

    print("[FAIL] 未返回发布页面")
    return False


def post_moments_private(content):
    """发布私密朋友圈（仅自己可见）"""
    print("=== 开始发布私密朋友圈（仅自己可见）===")
    print(f"内容长度: {len(content)} 字")
    print()

    # 步骤1：打开微信
    if not step1_open_wechat():
        return False

    # 步骤2：点击发现
    if not step2_click_discover():
        return False

    # 步骤3：点击朋友圈
    if not step3_click_moments():
        return False

    # 步骤4：长按相机（进入纯文字发布页面）
    if not step4_long_press_camera():
        return False

    # 步骤5：粘贴内容
    if not step5_paste_content(content):
        return False

    # 步骤6：点击"谁可以看"
    print("[6/8] 点击谁可以看...", end=" ", flush=True)

    # 粘贴内容后固定向上滚动一下，确保"谁可以看"按钮可见
    subprocess.run(["adb", "shell", "input", "swipe", "540", "1800", "540", "800", "300"], capture_output=True)
    time.sleep(0.5)

    clicked = False
    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text(xml, "谁可以看")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(0.5)
            clicked = True
            break
        time.sleep(0.3)
    if not clicked:
        print("[FAIL] 未找到'谁可以看'")
        return False
    print("[OK]")

    # 步骤7：点击"私密"
    if not step_click_private():
        return False

    # 步骤8：点击发表
    print("[8/8] 点击发表...", end=" ", flush=True)
    for attempt in range(3):
        xml = dump_ui()
        pos = find_by_text_exact(xml, "发表")
        if pos:
            tap(pos[0], pos[1])
            time.sleep(1)
            pkg = get_current_package()
            if pkg == "com.tencent.mm":
                print("[OK]")
                return True
        time.sleep(0.3)
    print("[FAIL] 发布失败")
    return False

# ─────────────── 命令行入口 ───────────────

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

if __name__ == "__main__":
    config = load_config()

    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python wechat_moments.py post \"内容\" [--group]    # 普通发布（可选分组）")
        print("  python wechat_moments.py private \"内容\"            # 私密发布（仅自己可见）")
        sys.exit(1)

    command = args[0]
    if command == "post":
        content = args[1] if len(args) > 1 else ""
        use_group = "--group" in args
        group_name = None
        if use_group:
            group_name = config.get("visibility", {}).get("group_name", "常用不可见人群")

        if not content:
            print("错误: 请提供要发布的内容")
            sys.exit(1)

        success = post_moments(content, group_name)
        sys.exit(0 if success else 1)

    elif command == "private":
        content = args[1] if len(args) > 1 else ""

        if not content:
            print("错误: 请提供要发布的内容")
            sys.exit(1)

        success = post_moments_private(content)
        sys.exit(0 if success else 1)
