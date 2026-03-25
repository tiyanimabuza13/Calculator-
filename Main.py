
from flask import Flask, request, jsonify, render_template_string
import os, base64, json, datetime
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256

app = Flask(__name__)

# ---------------- CONFIG ----------------
SETTINGS_FILE = ".app_metadata.json"
VAULT_FOLDER = "vault_storage"
PASSCODE = "1234"

if not os.path.exists(VAULT_FOLDER):
    os.makedirs(VAULT_FOLDER)

# ---------------- CRYPTO ----------------
def derive_key(passcode, salt):
    return PBKDF2(passcode, salt, dkLen=32, count=100000, hmac_hash_module=SHA256)

def encrypt_file(data, key):
    file_id = base64.urlsafe_b64encode(get_random_bytes(8)).decode()
    iv = get_random_bytes(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    encrypted, tag = cipher.encrypt_and_digest(data)

    with open(f"{VAULT_FOLDER}/{file_id}.bin", "wb") as f:
        f.write(iv + tag + encrypted)

    return file_id

def decrypt_file(file_id, key):
    with open(f"{VAULT_FOLDER}/{file_id}.bin", "rb") as f:
        iv = f.read(12)
        tag = f.read(16)
        data = f.read()

    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(data, tag)

# ---------------- SETTINGS ----------------
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        return json.load(open(SETTINGS_FILE))
    else:
        data = {"salt": base64.b64encode(get_random_bytes(16)).decode(), "files": {}}
        json.dump(data, open(SETTINGS_FILE, "w"))
        return data

def save_settings(data):
    json.dump(data, open(SETTINGS_FILE, "w"))

settings = load_settings()
salt = base64.b64decode(settings["salt"])
key = derive_key(PASSCODE, salt)

# ---------------- UI ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>RandyX Vault</title>
<style>
body {background:#111;color:white;text-align:center;font-family:Arial;}
button{width:60px;height:60px;margin:5px;font-size:20px;}
input{width:240px;height:40px;font-size:20px;text-align:right;}
.hidden{display:none;}
img{max-width:200px;margin-top:10px;}
</style>
</head>
<body>

<h2>🔥 Calculator</h2>
<input id="display" readonly><br>

<div id="calc">
<button onclick="p('7')">7</button>
<button onclick="p('8')">8</button>
<button onclick="p('9')">9</button>
<button onclick="p('/')">/</button><br>
<button onclick="p('4')">4</button>
<button onclick="p('5')">5</button>
<button onclick="p('6')">6</button>
<button onclick="p('*')">*</button><br>
<button onclick="p('1')">1</button>
<button onclick="p('2')">2</button>
<button onclick="p('3')">3</button>
<button onclick="p('-')">-</button><br>
<button onclick="p('0')">0</button>
<button onclick="calc()">=</button>
<button onclick="clr()">C</button>
<button onclick="p('+')">+</button>
</div>

<div id="vault" class="hidden">
<h2>🔐 Vault</h2>
<input type="file" id="file"><br><br>
<button onclick="upload()">Hide File</button>
<button onclick="lock()">Lock</button>

<div id="files"></div>
<img id="preview">
</div>

<script>
let exp="";

function p(v){exp+=v;display.value=exp;}
function clr(){exp="";display.value="";}
function calc(){
 fetch("/calc",{method:"POST",headers:{'Content-Type':'application/json'},
 body:JSON.stringify({exp:exp})})
 .then(r=>r.json()).then(d=>{
  if(d.vault){document.getElementById("calc").style.display="none";
              document.getElementById("vault").classList.remove("hidden");
              loadFiles();}
  else display.value=d.result;
  exp="";
 });
}

function upload(){
 let f=document.getElementById("file").files[0];
 let reader=new FileReader();
 reader.onload=function(){
  fetch("/upload",{method:"POST",headers:{'Content-Type':'application/json'},
  body:JSON.stringify({data:reader.result})})
  .then(()=>loadFiles());
 };
 reader.readAsDataURL(f);
}

function loadFiles(){
 fetch("/files").then(r=>r.json()).then(d=>{
  let html="";
  for(let f in d){
    html+=`<button onclick="view('${f}')">${d[f]}</button>`;
  }
  document.getElementById("files").innerHTML=html;
 });
}

function view(id){
 fetch("/view/"+id).then(r=>r.json()).then(d=>{
  document.getElementById("preview").src=d.data;
 });
}

function lock(){location.reload();}
</script>

</body>
</html>
"""

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template_string(HTML)

@app.route("/calc", methods=["POST"])
def calc():
    exp = request.json["exp"]
    if exp == PASSCODE:
        return jsonify({"vault": True})
    try:
        return jsonify({"result": eval(exp)})
    except:
        return jsonify({"result": "Error"})

@app.route("/upload", methods=["POST"])
def upload():
    data = request.json["data"].split(",")[1]
    raw = base64.b64decode(data)

    fid = encrypt_file(raw, key)
    settings["files"][fid] = f"file_{len(settings['files'])}"
    save_settings(settings)

    return jsonify({"ok": True})

@app.route("/files")
def files():
    return jsonify(settings["files"])

@app.route("/view/<fid>")
def view(fid):
    raw = decrypt_file(fid, key)
    encoded = base64.b64encode(raw).decode()
    return jsonify({"data": "data:image/png;base64," + encoded})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

