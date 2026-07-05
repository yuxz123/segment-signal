#!/bin/bash
# ============================================================
#  APK 构建脚本（国内镜像加速版）
# ============================================================
#  用法:
#    cd /mnt/c/Users/a7151/Desktop/小区间势段信号系统_安卓版
#    bash build_apk.sh
#
#  首次构建约 30-60 分钟（下载 NDK/SDK ~700MB）
#  后续构建约 5-10 分钟
# ============================================================

set -e

PROJECT_DIR="/mnt/c/Users/a7151/Desktop/小区间势段信号系统_安卓版"
cd "$PROJECT_DIR"

echo "========================================"
echo "  构建 APK..."
echo "  项目: $PROJECT_DIR"
echo "  时间: $(date)"
echo "========================================"
echo ""

# 确保 pip 用国内源
export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

# 设置 Android SDK 国内镜像（腾讯云加速）
# Buildozer 会通过 sdkmanager 下载，设置代理变量
export ANDROID_SDK_ROOT="$HOME/.buildozer/android/platform/android-sdk"

echo "开始构建..."
echo ""

# 构建 debug APK
buildozer android debug

# 检查结果
APK_PATH="$PROJECT_DIR/bin/segmentsignal-1.0-debug.apk"
if [ -f "$APK_PATH" ]; then
    SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo ""
    echo "========================================"
    echo "  [OK] 构建成功！"
    echo ""
    echo "  APK: $(wslpath -w "$APK_PATH")"
    echo "  大小: $SIZE"
    echo ""
    echo "  传到手机安装："
    echo "    方法1: USB线复制APK文件到手机，文件管理器打开安装"
    echo "    方法2: 电脑开启热点，手机连上后："
    echo "           cd bin && python3 -m http.server 8080"
    echo "           手机浏览器打开 http://YOUR_IP:8080 下载"
    echo "========================================"
else
    echo ""
    echo "[FAIL] 构建失败，检查上方错误"
    echo "常见问题："
    echo "  1. SDK下载失败 → 重试几次，有时会断"
    echo "  2. 内存不足 → 关掉不需要的程序"
    echo "  3. 磁盘空间不足 → 清理 ~/.buildozer 后重试"
    exit 1
fi
