[app]

title = Sakay Ano Tara

package.name = sakayanotara
package.domain = org.aisat

source.dir = .
source.include_exts = py,kv,db,png,jpg,jpeg,ttf,json

version = 1.0

requirements = python3,kivy,kivymd,pillow

orientation = portrait

fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b

android.permissions = INTERNET
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
