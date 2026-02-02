[app]
title = Boshkash Academy
package.name = boshkashacademy
package.domain = com.boshkash.academy
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js,json,db,ttf
version = 1.0.0
requirements = python3,flask,flask-sqlalchemy,flask-login,fpdf,qrcode,pillow,flask-cors,webview
orientation = portrait
fullscreen = 1
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 31
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/ios-control/ios-deploy
ios.ios_deploy_branch = master

[buildozer]
log_level = 2
warn_on_root = 1
