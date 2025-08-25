import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkinter.scrolledtext import ScrolledText

def log(msg):
    log_text.config(state='normal')
    log_text.insert('end', msg + '\n')
    log_text.see('end')
    log_text.config(state='disabled')

def show_checked():
    checked = []
    for var_key, (var, label) in checkboxes.items():
        if var.get():
            checked.append(f"{var_key} ({label})")
    if checked:
        msg = "Checked:\n" + "\n".join(checked)
    else:
        msg = "No checkbox is checked."
    log("Show Checked button pressed.")
    log(f"Result: {msg.replace(chr(10), '; ')}")
    # Simulate progress bar activity
    progress_bar.start(10)
    root.after(500, progress_bar.stop)  # Simulate some processing delay
    messagebox.showinfo("Checked Boxes", msg)

def select_directory(idx):
    dir_path = filedialog.askdirectory()
    if dir_path:
        dir_vars[idx].set(dir_path)
        log(f"Directory {idx+1} selected: {dir_path}")

def on_checkbox_toggle(var_key):
    var, label = checkboxes[var_key]
    log(f"Checkbox '{label}' ({var_key}) set to {var.get()}")

root = tk.Tk()
root.title("GUI with Checkboxes, Directories, Progress, and Logging")

# --- Directory selectors ---
dir_vars = [tk.StringVar(value="No directory selected") for _ in range(2)]

for i in range(2):
    frame = tk.Frame(root)
    frame.pack(fill='x', pady=2)
    btn = tk.Button(frame, text=f"Select Directory {i+1}", command=lambda idx=i: select_directory(idx))
    btn.pack(side='left')
    lbl = tk.Label(frame, textvariable=dir_vars[i], width=50, anchor='w')
    lbl.pack(side='left', padx=5)

# --- Progress bar ---
progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='indeterminate')
progress_bar.pack(pady=6)

# --- Checkboxes ---
checkbox_info = [
    ('apple',     'Apple Fruit'),
    ('banana',    'Banana Fruit'),
    ('car',       'Sports Car'),
    ('python',    'Python Language'),
    ('cat',       'Cute Cat'), 
    ('moon',      'The Moon'),
    ('diamond',   'Diamond Gem'),
    ('rocket',    'Space Rocket'),
    ('music',     'Music Notes'),
    ('flower',    'Beautiful Flower'),
]

checkboxes = {}

for key, label in checkbox_info:
    var = tk.BooleanVar()
    # Use command to log when checkbox changes
    chk = tk.Checkbutton(root, text=label, variable=var, command=lambda k=key: on_checkbox_toggle(k))
    chk.pack(anchor='w')
    checkboxes[key] = (var, label)

btn = tk.Button(root, text="Show Checked", command=show_checked)
btn.pack(pady=10)

# --- Logging window ---
log_label = tk.Label(root, text="Log Output:")
log_label.pack(anchor='w')
log_text = ScrolledText(root, height=7, width=70, state='disabled', font=("consolas", 9))
log_text.pack(padx=5, pady=(0,8), fill='both', expand=False)

root.mainloop()