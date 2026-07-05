#!/bin/bash
# ============================================================
#  WSL 一键搭建脚本（国内镜像加速版）
# ============================================================
#  前置步骤（PowerShell 管理员运行）:
#    1. wsl --install          ← 默认装C盘
#    2. 若要装D盘：见下方"WSL装D盘"说明
#    3. 重启 → 进入 Ubuntu → 设用户名密码
#    4. cd /mnt/c/Users/a7151/Desktop/小区间势段信号系统_安卓版
#    5. bash setup_wsl.sh
# ============================================================
#
#  【WSL 装 D 盘方法】（在 PowerShell 管理员中）:
#    wsl --install                                    # 先正常安装
#    wsl --shutdown                                   # 关闭WSL
#    wsl --export Ubuntu D:\WSL\ubuntu.tar            # 导出
#    wsl --unregister Ubuntu                          # 注销C盘的
#    wsl --import Ubuntu D:\WSL\Ubuntu D:\WSL\ubuntu.tar  # 导入到D盘
#    del D:\WSL\ubuntu.tar                            # 删掉临时tar
#    重新打开Ubuntu即可（需重新设用户名）
# ============================================================

set -e

MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
APT_MIRROR="mirrors.tuna.tsinghua.edu.cn"

echo "========================================"
echo "  小区间势段信号系统 - WSL 构建环境搭建"
echo "  pip镜像: $MIRROR"
echo "========================================"
echo ""

# 1. 换 apt 国内源
echo "[1/6] 配置 apt 清华镜像源..."
sudo sed -i "s@http://.*archive.ubuntu.com@http://$APT_MIRROR@g" /etc/apt/sources.list 2>/dev/null || true
sudo sed -i "s@http://.*security.ubuntu.com@http://$APT_MIRROR@g" /etc/apt/sources.list 2>/dev/null || true
sudo apt update -y && sudo apt upgrade -y

# 2. 安装 Buildozer 系统依赖
echo ""
echo "[2/6] 安装系统依赖..."
sudo apt install -y \
    python3 python3-pip python3-dev \
    git autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev \
    libtinfo5 cmake libffi-dev libssl-dev \
    libltdl-dev \
    openjdk-17-jdk-headless \
    unzip zip lld python3-venv

# 3. 配置 pip 国内源
echo ""
echo "[3/6] 配置 pip 清华源..."
pip3 config set global.index-url "$MIRROR"
pip3 config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 4. 安装 Buildozer + Cython
echo ""
echo "[4/6] 安装 Buildozer..."
pip3 install --upgrade buildozer Cython

# 5. 安装项目依赖
echo ""
echo "[5/6] 安装项目 Python 依赖..."
cd /mnt/c/Users/a7151/Desktop/小区间势段信号系统_安卓版
pip3 install kivy==2.3.0 pandas numpy requests openpyxl

# 6. 配置 buildozer 使用国内镜像下载 NDK/SDK
echo ""
echo "[6/6] 配置 Buildozer..."
mkdir -p ~/.buildozer
cat > ~/.buildozer/android_default.env << 'EOF'
# Android SDK 国内镜像（腾讯云）
export ANDROID_SDK_HOME=$HOME/.buildozer/android/platform/android-sdk
# 以下变量加速 buildozer 首次下载
EOF

echo ""
echo "========================================"
echo "  [OK] 环境搭建完成！"
echo ""
echo "  验证: buildozer version"
echo "  下一步: bash build_apk.sh"
echo ""
echo "  提示: 首次构建会下载 NDK(~500MB) + SDK(~200MB)"
echo "        请保持网络通畅，约需 30-60 分钟"
echo "========================================"
