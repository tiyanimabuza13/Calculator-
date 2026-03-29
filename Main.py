import tkinter as tk
from tkinter import messagebox
import json
import os

# ---------------------------
# FILES
# ---------------------------
USER_FILE = "users.json"
HISTORY_FILE = "history.txt"
VAULT_FILE = "vault.txt"

# ---------------------------
# BASIC STORAGE
# ---------------------------
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# ---------------------------
# LOGIN SYSTEM
# ---------------------------
def register():
    username = user_entry.get()
    password = pass_entry.get()

    users = load_users()

    if username in users:
        messagebox.showerror("Error", "User already exists")
    else:
        users[username] = password
        save_users(users)
        messagebox.showinfo("Success", "Registered successfully")

def login():
    username = user_entry.get()
    password = pass_entry.get()

    users = load_users()

    if username in users and users[username] == password:
        messagebox.showinfo("Success", "Login successful")
        open_calculator()
    else:
        messagebox.showerror("Error", "Invalid login")

# ---------------------------
# CALCULATOR WINDOW
# ---------------------------
def open_calculator():
    calc = tk.Toplevel(root)
    calc.title("Smart Calculator")
    calc.geometry("300x450")
    calc.configure(bg="#1e1e1e")

    expression = ""

    entry = tk.Entry(calc, font=("Arial", 18), bg="#333", fg="white", bd=0)
    entry.pack(fill="both", padx=10, pady=10)

    def press(value):
        nonlocal expression
        expression += str(value)
        entry.delete(0, tk.END)
        entry.insert(0, expression)

    def equal():
        nonlocal expression
        try:
            result = str(eval(expression))
            save_history(expression + " = " + result)
            entry.delete(0, tk.END)
            entry.insert(0, result)
            expression = result
        except:
            entry.delete(0, tk.END)
            entry.insert(0, "Error")
            expression = ""

    def clear():
        nonlocal expression
        expression = ""
        entry.delete(0, tk.END)

    # Buttons
    buttons = [
        '7','8','9','/',
        '4','5','6','*',
        '1','2','3','-',
        '0','.','=','+'
    ]

    frame = tk.Frame(calc, bg="#1e1e1e")
    frame.pack()

    row = 0
    col = 0

    for b in buttons:
        action = lambda x=b: press(x) if x != '=' else equal()
        tk.Button(frame, text=b, width=5, height=2,
                  command=action, bg="#333", fg="white").grid(row=row, column=col)
        col += 1
        if col > 3:
            col = 0
            row += 1

    tk.Button(calc, text="Clear", command=clear, bg="red", fg="white").pack(fill="both")
    tk.Button(calc, text="History", command=view_history).pack(fill="both")
    tk.Button(calc, text="Vault 🔒", command=open_vault).pack(fill="both")

# ---------------------------
# HISTORY
# ---------------------------
def save_history(text):
    with open(HISTORY_FILE, "a") as f:
        f.write(text + "\n")

def view_history():
    if not os.path.exists(HISTORY_FILE):
        messagebox.showinfo("History", "No history yet")
        return

    with open(HISTORY_FILE, "r") as f:
        data = f.read()

    messagebox.showinfo("History", data)

# ---------------------------
# VAULT (SECRET STORAGE)
# ---------------------------
def open_vault():
    vault = tk.Toplevel(root)
    vault.title("Secure Vault")
    vault.geometry("300x300")

    text = tk.Text(vault)
    text.pack()

    if os.path.exists(VAULT_FILE):
        with open(VAULT_FILE, "r") as f:
            text.insert("1.0", f.read())

    def save():
        with open(VAULT_FILE, "w") as f:
            f.write(text.get("1.0", tk.END))
        messagebox.showinfo("Saved", "Vault saved")

    tk.Button(vault, text="Save", command=save).pack()

# ---------------------------
# MAIN LOGIN UI
# ---------------------------
root = tk.Tk()
root.title("Secure App Login")
root.geometry("300x200")
root.configure(bg="#121212")

tk.Label(root, text="Username", fg="white", bg="#121212").pack()
user_entry = tk.Entry(root)
user_entry.pack()

tk.Label(root, text="Password", fg="white", bg="#121212").pack()
pass_entry = tk.Entry(root, show="*")
pass_entry.pack()

tk.Button(root, text="Login", command=login).pack(pady=5)
tk.Button(root, text="Register", command=register).pack()

root.mainloop()
