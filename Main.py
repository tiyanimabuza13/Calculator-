import os
import json
import base64
import datetime
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256

import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
import io

# --- Configuration & Security Parameters ---
# Use a complex passcode. In a real app, this is user-definable.
SECRET_PASSCODE = "1234"
# Name of the settings file (obfuscated name)
SETTINGS_FILE = ".app_metadata.dat"
# Folder to store encrypted files (obfuscated name)
VAULT_FOLDER = ".app_data_storage"
# PBKDF2 Iterations (higher is more secure, slower)
KDF_ITERATIONS = 100000

# Ensure the vault folder exists
if not os.path.exists(VAULT_FOLDER):
    os.makedirs(VAULT_FOLDER)


# --- Advanced Cryptography (PyCryptodome) ---

class CryptoEngine:
    @staticmethod
    def derive_key(passcode, salt):
        """Derives a 256-bit AES key from a passcode and salt using PBKDF2."""
        return PBKDF2(passcode, salt, dkLen=32, count=KDF_ITERATIONS, hmac_hash_module=SHA256)

    @staticmethod
    def encrypt_file(in_filename, derived_key):
        """
        Encrypts a file using AES-256-GCM and deletes the original.
        Returns the unique ID of the encrypted file.
        """
        file_id = base64.urlsafe_b64encode(get_random_bytes(16)).decode().strip("=")
        out_filename = os.path.join(VAULT_FOLDER, file_id + ".enc")

        # 1. Generate a random IV for GCM
        iv = get_random_bytes(12)
        cipher = AES.new(derived_key, AES.MODE_GCM, nonce=iv)

        try:
            with open(in_filename, "rb") as f_in, open(out_filename, "wb") as f_out:
                # 2. Encrypt the file data
                encrypted_data, tag = cipher.encrypt_and_digest(f_in.read())
                # 3. Save [IV] [Tag] [EncryptedData]
                f_out.write(iv)
                f_out.write(tag)
                f_out.write(encrypted_data)

            # 4. Delete the original unencrypted file
            os.remove(in_filename)
            return file_id
        except Exception as e:
            if os.path.exists(out_filename):
                os.remove(out_filename)
            raise e

    @staticmethod
    def decrypt_file(file_id, derived_key):
        """
        Reads, verifies, and decrypts an encrypted file in memory.
        Returns the raw, decrypted bytes.
        """
        in_filename = os.path.join(VAULT_FOLDER, file_id + ".enc")
        if not os.path.exists(in_filename):
            raise FileNotFoundError(f"Vault file '{in_filename}' not found.")

        with open(in_filename, "rb") as f_in:
            # 1. Read [IV] [Tag] [EncryptedData]
            iv = f_in.read(12)
            tag = f_in.read(16)
            encrypted_data = f_in.read()

        # 2. Initialize GCM with the extracted IV
        cipher = AES.new(derived_key, AES.MODE_GCM, nonce=iv)
        # 3. Decrypt and verify tag (authentication)
        try:
            decrypted_bytes = cipher.decrypt_and_verify(encrypted_data, tag)
            return decrypted_bytes
        except ValueError:
            raise ValueError("Decryption/Verification failed. Key may be invalid.")


# --- Settings & State Management ---

class AppSettings:
    def __init__(self):
        self.salt = None
        self.encrypted_file_map = {}
        self.load()

    def load(self):
        """Loads app settings. Initializes salt if needed."""
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Settings file contains base64 encoded salt and a map of files
                self.salt = base64.b64decode(data['salt'])
                self.encrypted_file_map = data.get('file_map', {})
        else:
            # First run: Generate a secure random salt
            self.salt = get_random_bytes(32)
            self.save()

    def save(self):
        """Saves current settings to disk."""
        data = {
            'salt': base64.b64encode(self.salt).decode(),
            'file_map': self.encrypted_file_map
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def add_file_to_vault(self, original_path, file_id):
        """Maps an original filename to its unique ID in the vault."""
        filename = os.path.basename(original_path)
        # Store metadata: original name, timestamp, type (inferred)
        self.encrypted_file_map[file_id] = {
            'name': filename,
            'added_on': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'type': self._infer_type(filename)
        }
        self.save()

    def _infer_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']: return 'image'
        if ext in ['.mp4', '.avi', '.mov']: return 'video'
        return 'document'


# --- UI Screens ---

class CalculatorScreen(Screen):
    def __init__(self, settings, **kwargs):
        super(CalculatorScreen, self).__init__(**kwargs)
        self.settings = settings
        self.expression = ""

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.display = Label(text="0", font_size=50, halign="right", valign="middle", size_hint_y=0.2)
        self.display.bind(size=self.display.setter('text_size'))
        main_layout.add_widget(self.display)

        button_grid = GridLayout(cols=4, spacing=5)
        buttons = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', 'C', '0', '.', '+']
        for btn_text in buttons:
            btn = Button(text=btn_text, font_size=30, background_color=(0.1, 0.1, 0.1, 1))
            btn.bind(on_press=self.on_button_press)
            button_grid.add_widget(btn)

        equals_btn = Button(text='=', font_size=30, size_hint_y=None, height=80, background_color=(0, 0.5, 0.8, 1))
        equals_btn.bind(on_press=self.on_solution)

        main_layout.add_widget(button_grid)
        main_layout.add_widget(equals_btn)
        self.add_widget(main_layout)

    def on_button_press(self, instance):
        if instance.text == 'C':
            self.expression = ""
            self.display.text = "0"
        else:
            if self.display.text in ["0", "Error"]: self.expression = instance.text
            else: self.expression += instance.text
            self.display.text = self.expression

    def on_solution(self, instance):
        if self.expression == SECRET_PASSCODE:
            # Derive the AES key on unlock, then pass it to the vault
            app = App.get_running_app()
            app.active_aes_key = CryptoEngine.derive_key(SECRET_PASSCODE, self.settings.salt)
            self.manager.current = 'vault'
            self.expression, self.display.text = "", "0"
            return

        try:
            # Production: Replace 'eval' with a safer expression parser
            self.display.text = str(eval(self.expression))
            self.expression = self.display.text
        except Exception:
            self.display.text, self.expression = "Error", ""


class VaultScreen(Screen):
    def __init__(self, settings, **kwargs):
        super(VaultScreen, self).__init__(**kwargs)
        self.settings = settings

        # --- Vault UI Layout ---
        main_layout = BoxLayout(orientation='vertical', padding=15, spacing=15)
        # Minimal header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(text="MEMBER VAULT", font_size=24, color=(0.8, 0, 0, 1), bold=True))
        back_btn = Button(text="Lock", size_hint_x=None, width=80)
        back_btn.bind(on_press=self.on_back)
        header.add_widget(back_btn)
        main_layout.add_widget(header)

        # File list area (Simple for MVP)
        self.file_list_label = Label(text="Encrypt/Decrypt a sample image file to begin.", size_hint_y=0.2, halign='left')
        self.file_list_label.bind(size=self.file_list_label.setter('text_size'))
        main_layout.add_widget(self.file_list_label)

        # Content display (Image viewer MVP)
        self.image_display = Image(source='', size_hint_y=0.5, allow_stretch=True, keep_ratio=True)
        main_layout.add_widget(self.image_display)

        # Action buttons
        button_layout = BoxLayout(size_hint_y=0.15, spacing=10)
        encrypt_btn = Button(text="[color=ffffff]Add Image File[/color]", markup=True, background_color=(0, 0.6, 0.3, 1))
        encrypt_btn.bind(on_press=self.on_add_sample_image)
        decrypt_btn = Button(text="[color=ffffff]View Decrypted[/color]", markup=True, background_color=(0.6, 0, 0, 1))
        decrypt_btn.bind(on_press=self.on_decrypt_sample)
        button_layout.add_widget(encrypt_btn)
        button_layout.add_widget(decrypt_btn)
        main_layout.add_widget(button_layout)

        self.add_widget(main_layout)

    def _get_active_key(self):
        key = App.get_running_app().active_aes_key
        if not key:
            self.manager.current = 'calculator'
            raise ValueError("AES key not active.")
        return key

    def on_add_sample_image(self, instance):
        """
        MVP: Hardcoded path to an image file.
        In a real app, this launches a native File Picker.
        """
        SAMPLE_IMAGE_FILE = "sample_image.jpg" # Make sure this exists in your project folder!

        if not os.path.exists(SAMPLE_IMAGE_FILE):
            self.file_list_label.text = f"Error: '{SAMPLE_IMAGE_FILE}' must exist for MVP testing."
            return

        try:
            key = self._get_active_key()
            file_id = CryptoEngine.encrypt_file(SAMPLE_IMAGE_FILE, key)
            self.settings.add_file_to_vault(SAMPLE_IMAGE_FILE, file_id)
            self.file_list_label.text = f"File Added to Vault.\nOriginal deleted.\nVault ID: {file_id}.enc"
            self.sample_file_id = file_id # Keep track of the added ID
            self.image_display.source = "" # Clear previous image
        except Exception as e:
            self.file_list_label.text = f"Encryption Error: {e}"

    def on_decrypt_sample(self, instance):
        """MVP: Decrypts and displays the *one* sample image file."""
        if not hasattr(self, 'sample_file_id') or not self.sample_file_id:
            self.file_list_label.text = "Error: Add an image file first."
            return

        try:
            key = self._get_active_key()
            decrypted_bytes = CryptoEngine.decrypt_file(self.sample_file_id, key)

            # In Kivy, we use CoreImage to load image data from raw bytes (io.BytesIO)
            image_data = io.BytesIO(decrypted_bytes)
            # Infer mimetype (MVP: assumes JPG)
            core_img = CoreImage(image_data, ext='jpg')
            self.image_display.texture = core_img.texture
            self.file_list_label.text = "Decrypted image displayed from memory."
        except Exception as e:
            self.file_list_label.text = f"Decryption Error: {e}"

    def on_back(self, instance):
        # Lock the vault: Remove the derived key from memory
        App.get_running_app().active_aes_key = None
        self.sample_file_id = None
        self.image_display.source = "" # Clear image
        self.image_display.texture = None
        self.file_list_label.text = "Vault locked. Data secured."
        self.manager.current = 'calculator'


# --- Main App ---

class CalculatorVaultImprovedApp(App):
    def build(self):
        Window.size = (360, 640)
        self.title = "Calculator" # External name
        # Placeholder for derived AES key (Keep in memory, never on disk)
        self.active_aes_key = None
        # Load app settings/salt/metadata
        self.settings = AppSettings()

        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(CalculatorScreen(self.settings, name='calculator'))
        sm.add_widget(VaultScreen(self.settings, name='vault'))
        return sm

if __name__ == '__main__':
    CalculatorVaultImprovedApp().run()
