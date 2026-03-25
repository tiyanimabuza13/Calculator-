import os
import sys

# --- 1. MANDATORY GRAPHICS FIX (Must be the absolute first thing) ---
# This tells Kivy to use the opengl32.dll file in your folder instead of the system hardware
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_GRAPHICS'] = 'gles'
os.environ['PATH'] = os.getcwd() + ";" + os.environ['PATH']

import json
import base64
import datetime
import io

# Cryptography
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256

# Kivy UI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage

# Native File Picker
from plyer import filechooser

# ... [The rest of your CryptoEngine, AppSettings, and UI classes remain the same] ...

































