[app]
title = 小区间势段信号
package.name = segmentsignal
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,ttf
version = 1.0
requirements = python3,kivy==2.3.0,pandas==v2.2.2,numpy==v1.26.4,requests,openpyxl,android
orientation = portrait
fullscreen = 0

# 权限
android.permissions = INTERNET
android.api = 34
android.minapi = 26
android.ndk = 25b
android.sdk = 34
android.gradle_dependencies = 
android.accept_sdk_license = True
android.allow_backup = True

# 图标 (可选)
# icon.filename = icon.png

# 日志
log_level = 1
warn_on_root = 1

# 签名 (debug版无需签名)
# android.keystore = 
# android.keyalias = 

# 本地 recipes（覆盖无法下载的源）
p4a.local_recipes = p4a_recipes

# ===== 国内加速设置 =====
# 若 SDK 下载太慢，可手动下载后指定路径:
# android.sdk_path = /path/to/your/android-sdk
# android.ndk_path = /path/to/your/android-ndk
# android.commandlinetools_url = https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
# android.ndk_url = https://dl.google.com/android/repository/android-ndk-r25b-linux.zip

[buildozer]
log_level = 2
