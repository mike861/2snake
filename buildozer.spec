[app]
title = Two Player Snake
package.name = twoplayersnake
package.domain = org.snake
source.dir = .
source.include_exts = py,png,jpg,wav,kv
version = 1.0

requirements = python3,kivy,kivymd,pygame

orientation = landscape

android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.presplash_color = #000000
android.presplash_lottie = 

[buildozer]
log_level = 2
warn_on_root = 1 