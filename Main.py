import os

# 1. SET THE 
import os
# --- 1. MANDATORY GRAPHICS FIX (Must be the absolute first thing) ---
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

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

# --- Configuration & Paths ---
SETTINGS_FILE = ".app_metadata.dat"
VAULT_FOLDER = ".app_data_storage"
KDF_ITERATIONS = 100000

if not os.path.exists(VAULT_FOLDER):
    os.makedirs(VAULT_FOLDER)

# --- Logic: Cryptography ---
class CryptoEngine:
    @staticmethod
    def derive_key(passcode, salt):
        return PBKDF2(passcode, salt, dkLen=32, count=KDF_ITERATIONS, hmac_hash_module=SHA256)

    @staticmethod
    def encrypt_file(in_filename, derived_key):
        file_id = base64.urlsafe_b64encode(get_random_bytes(16)).decode().strip("=")
        out_filename = os.path.join(VAULT_FOLDER, file_id + ".enc")
        iv = get_random_bytes(12)
        cipher = AES.new(derived_key, AES.MODE_GCM, nonce=iv)

        with open(in_filename, "rb") as f_in, open(out_filename, "wb") as f_out:
            encrypted_data, tag = cipher.encrypt_and_digest(f_in.read())
            f_out.write(iv + tag + encrypted_data)
        
        os.remove(in_filename) # Delete original after encryption
        return file_id

    @staticmethod
    def decrypt_file(file_id, derived_key):
        in_filename = os.path.join(VAULT_FOLDER, file_id + ".enc")
        with open(in_filename, "rb") as f_in:
            iv, tag, data = f_in.read(12), f_in.read(16), f_in.read()
        cipher = AES.new(derived_key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(data, tag)

# --- Logic: App Settings ---
class AppSettings:
    def __init__(self):
        self.salt = None
        self.passcode = "1234" # Default passcode
        self.encrypted_file_map = {}
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.salt = base64.b64decode(data['salt'])
                self.passcode = data.get('passcode', "1234")
                self.encrypted_file_map = data.get('file_map', {})
        else:
            self.salt = get_random_bytes(32)
            self.save()

    def save(self):
        data = {
            'salt': base64.b64encode(self.salt).decode(),
            'passcode': self.passcode,
            'file_map': self.encrypted_file_map
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def add_to_vault(self, original_path, file_id):
        name = os.path.basename(original_path)
        self.encrypted_file_map[file_id] = {
            'name': name,
            'added_on': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'ext': name.split('.')[-1] if '.' in name else 'jpg'
        }
        self.save()

# --- UI: Calculator (Entry Point) ---
class CalculatorScreen(Screen):
    def __init__(self, settings, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        self.expression = ""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.display = Label(text="0", font_size=50, size_hint_y=0.2, halign="right")
        layout.add_widget(self.display)

        grid = GridLayout(cols=4, spacing=5)
        btns = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', 'C', '0', '.', '+']
        for b in btns:
            btn = Button(text=b, font_size=30, background_color=(0.1, 0.1, 0.1, 1))
            btn.bind(on_press=self.on_click)
            grid.add_widget(btn)
        
        eq = Button(text='=', font_size=30, size_hint_y=None, height=80, background_color=(0, 0.5, 0.8, 1))
        eq.bind(on_press=self.on_eval)
        
        layout.add_widget(grid)
        layout.add_widget(eq)
        self.add_widget(layout)

    def on_click(self, inst):
        if inst.text == 'C': self.expression = ""
        else: self.expression += inst.text
        self.display.text = self.expression or "0"

    def on_eval(self, inst):
        if self.expression == self.settings.passcode:
            App.get_running_app().key = CryptoEngine.derive_key(self.settings.passcode, self.settings.salt)
            self.manager.current = 'vault'
        else:
            try: self.display.text = str(eval(self.expression))
            except: self.display.text = "Error"
        self.expression = ""

# --- UI: Vault (Secure Area) ---
class VaultScreen(Screen):
    def __init__(self, settings, **kwargs):
        super().__init__(**kwargs)
        self.settings = settings
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(text="MABUZA VAULT", bold=True, color=(1,0,0,1)))
        lock = Button(text="Lock", size_hint_x=None, width=80)
        lock.bind(on_press=self.on_lock)
        header.add_widget(lock)
        layout.add_widget(header)

        # Preview
        self.preview = Image(size_hint_y=0.4)
        layout.add_widget(self.preview)

        # File List
        self.scroll = ScrollView(size_hint_y=0.4)
        self.list_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)
        layout.add_widget(self.scroll)

        # Footer
        add_btn = Button(text="HIDE NEW IMAGE", size_hint_y=None, height=60, background_color=(0, 0.6, 0.2, 1))
        add_btn.bind(on_press=self.pick_file)
        layout.add_widget(add_btn)

        self.add_widget(layout)

    def on_enter(self): self.refresh()

    def refresh(self):
        self.list_layout.clear_widgets()
        for fid, meta in self.settings.encrypted_file_map.items():
            row = BoxLayout(size_hint_y=None, height=60, spacing=5)
            btn = Button(text=f"{meta['name']}\n{meta['added_on']}", markup=True)
            btn.bind(on_press=lambda x, f=fid: self.view(f))
            del_btn = Button(text="X", size_hint_x=None, width=50, background_color=(0.8,0,0,1))
            del_btn.bind(on_press=lambda x, f=fid: self.delete_file(f))
            row.add_widget(btn)
            row.add_widget(del_btn)
            self.list_layout.add_widget(row)

    def pick_file(self, inst):
        filechooser.open_file(on_selection=self.handle_pick)

    def handle_pick(self, selection):
        if selection:
            fid = CryptoEngine.encrypt_file(selection[0], App.get_running_app().key)
            self.settings.add_to_vault(selection[0], fid)
            self.refresh()

    def view(self, fid):
        try:
            data = CryptoEngine.decrypt_file(fid, App.get_running_app().key)
            ext = self.settings.encrypted_file_map[fid]['ext']
            img = CoreImage(io.BytesIO(data), ext=ext)
            self.preview.texture = img.texture
        except Exception as e: print(f"View Error: {e}")

    def delete_file(self, fid):
        path = os.path.join(VAULT_FOLDER, fid + ".enc")
        if os.path.exists(path): os.remove(path)
        del self.settings.encrypted_file_map[fid]
        self.settings.save()
        self.preview.texture = None
        self.refresh()

    def on_lock(self, inst):
        App.get_running_app().key = None
        self.preview.texture = None
        self.manager.current = 'calculator'

# --- Main App ---
class VaultApp(App):
    def build(self):
        self.title = "Calculator"
        self.key = None
        self.settings = AppSettings()
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(CalculatorScreen(self.settings, name='calculator'))
        sm.add_widget(VaultScreen(self.settings, name='vault'))
        return sm

if __name__ == '__main__':
    VaultApp().run()
