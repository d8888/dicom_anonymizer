import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from tkinter.scrolledtext import ScrolledText
import pydicom
import os
from pydicom.errors import InvalidDicomError
import pandas as pd
import shutil
import re
import pydicom

def log(msg):
    log_text.config(state='normal')
    log_text.insert('end', msg + '\n')
    log_text.see('end')
    log_text.config(state='disabled')

def start_anonymize():
    input_dir = dir_vars[0].get()
    output_dir = dir_vars[1].get()

    # check if both input_dir and output_dir are set
    if input_dir == "No directory selected" or output_dir == "No directory selected":
        messagebox.showerror("Directory Not Set", "Please set both input and output directories.")
        return

    # check if input_dir and output_dir are the same
    if input_dir == output_dir:
        messagebox.showerror("Directory Error", "Input and output directories cannot be the same.")
        return

    # check if output_dir is empty directory
    if os.listdir(output_dir):
        # show a yes, no messagebox
        if messagebox.askyesno("Output Directory Not Empty", "The output directory is not empty. Do you want to continue?"):
            pass  # User chose to continue
        else:
            return  # User chose not to continue
    # check if input_dir exists
    if not os.path.exists(input_dir):
        messagebox.showerror("Input Directory Not Found", "The input directory does not exist.")
        return

    checked = []
    checked_labels = []
    for label, (var, fulltag) in checkboxes.items():
        if var.get():
            checked.append(fulltag)
            checked_labels.append(label)
    if checked:
        msg = "Following DICOM tags will be anonymized:\n" + "\n".join(checked_labels)
    else:
        messagebox.showerror("No DICOM Tag Selected", "Please select at least one DICOM tag to anonymize")
        return
    log("Show Checked button pressed.")
    log(f"Result: {msg}")
    batch_anonymize(progress_bar, input_dir, output_dir, checked)
    return

def select_directory(idx):
    dir_path = filedialog.askdirectory()
    if dir_path:
        dir_vars[idx].set(dir_path)
        log(f"Directory {idx+1} selected: {dir_path}")

def on_checkbox_toggle(var_key):
    var, label = checkboxes[var_key]
    #log(f"Checkbox '{label}' ({var_key}) set to {var.get()}")
    return


def get_dicom_tags(infile):
    ds = pydicom.dcmread(infile)
    rst = [str(elem.tag) + " " + str(elem.name) for elem in ds]
    return rst

def enumerate_all_dicom_tags(input_dir):
    # recursively print all file names in INPUT_DIR, note that INPUT_DIR is nested
    rst = []
    idx = 0 
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            print(root + "\\" + filename)
            if idx % 100 == 0:
                print(idx)
            idx = idx + 1
            rst = rst + get_dicom_tags(root+"\\"+filename)
            rst = list(set(rst))


def copy_as_is(root, filename, input_dir, output_dir):
    # copy the file as is using shutil
    outroot = output_dir  + root[len(input_dir):]
    if not os.path.exists(outroot):
        os.makedirs(outroot)
    shutil.copy(root + "\\" + filename, outroot + "\\" + filename)

def make_value_anonymized(data_element):
    data_element.value = "_"
    return

def make_value_zero_age(data_element):
    data_element.value = "000Y"
    return

def make_value_date(data_element):
    data_element.value = "19000101"
    return

def make_value_time(data_element):
    data_element.value = "070907.0705"
    return

def remove_space(input):
    return re.sub(r'\s+', '', input)

def remove_value(remove_tags, data_element, func):
    for line in remove_tags.splitlines():
        line=line.strip()
        m = re.search(r'\((\w+), (\w+)\)', line)
        if not m:
            continue
        val = "("+m.group(1) + ", "+ m.group(2)+")"
        if remove_space(str(data_element.tag)) == remove_space(str(val)):
            func(data_element)
            return

def retrieve_value(target_tags, data_element, rst):
    for line in target_tags.splitlines():
        line=line.strip()
        m = re.search(r'\((\w+), (\w+)\)', line)
        if not m:
            continue
        val = "("+m.group(1) + ", "+ m.group(2)+")"
        if str(data_element.tag) == str(val):
            rst.append((val, data_element.value))
            return


def anonymize_callback(dataset, data_element, target):
    tags_anon = ""
    tags_makedate = ""
    tags_maketime = ""  

    for t in target:
        fulltag, method = t.split("|")
        fulltag = fulltag.strip()
        method = method.strip()
        if method == "anon":
            tags_anon = tags_anon + fulltag + "\n"
        elif method == "date":
            tags_makedate = tags_makedate + fulltag + "\n"
        elif method == "time":
            tags_maketime = tags_maketime + fulltag + "\n"  
        else:
            messagebox.showerror("Internal Error", "Invalid anonymize method:"+str(t))
            return

    remove_value(tags_anon, data_element, make_value_anonymized)
    remove_value(tags_makedate, data_element, make_value_date)
    remove_value(tags_maketime, data_element, make_value_time)
    return

def retrieve_callback(dataset, data_element, rst):
    preserved_tags = """
(0008, 0020) Study Date
(0010, 0030) Patient's Birth Date
(0008, 0050) Accession Number    
(0010, 0040) Patient's Sex    
(0010, 1010) Patient's Age
"""    
    retrieve_value(preserved_tags, data_element, rst)
    return

def anonymize_dicom_file(infile, target):
    ds = pydicom.dcmread(infile)
    ds.remove_private_tags()
    anon_functor = anonymize_functor(target)
    ds.walk(anon_functor) 
    return ds

class anonymize_functor:
    def __init__(self, target):
        self.target = target
    def __call__(self, dataset, data_element):
        anonymize_callback(dataset, data_element, self.target)

class retrieve_functor:
    def __init__(self):
        self.rst = []
    def __call__(self, dataset, data_element):
        retrieve_callback(dataset, data_element, self.rst)

def retrieve_data_from_dicom_file(infile):
    ds = pydicom.dcmread(infile)
    tmp =  retrieve_functor()
    ds.walk(tmp) 

    rst = {}
    for elem in tmp.rst:
        rst[elem[0]]=elem[1]

    return rst, ds

def batch_anonymize(progress_bar, input_dir, output_dir, target):
    rst = []
    idx = 0 
    already_processed = set()

    total_file_count = sum([len(files) for r, d, files in os.walk(input_dir)])
    log("Total files to process: {}".format(total_file_count))

    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            idx = idx + 1
            progress_bar.step(1/total_file_count*100)
            
            rst = {}
            ds = None

            try:
                # get age and sex
                rst, ds = retrieve_data_from_dicom_file(root+"\\"+filename)
                
                # change the topmost directory of root from input_dir to output_dir
                outroot = output_dir  + root[len(input_dir):]
                ds = anonymize_dicom_file(root+"\\"+filename, target)

                # make sure the output directory exists
                if not os.path.exists(outroot):
                    os.makedirs(outroot)

                ds.save_as(outroot+"\\"+filename)

            except InvalidDicomError as e:
                if filename.endswith(".nii") or filename.endswith(".DS_Store"):
                    copy_as_is(root, filename, input_dir, output_dir)
                else:
                    log("Probably bad dicom file or unknown file, copy AS IS:")
                    log(root + "\\" + filename)
                    copy_as_is(root, filename, input_dir, output_dir)
                continue
            except KeyError as e:
                log("fail to grab patient data")
                log(root + "\\" + filename)
                log(e)
                log(rst)
                # dump all tags from ds
                for elem in ds:
                    log(str(elem.tag) + " " + str(elem.name) + " " + str(elem.value))
                continue
        
    log("Job complete! total {num} file processed".format(num=idx))

# global settings
DICOM_TAGS = """
(0008, 0080) Institution Name | anon
(0008, 1048) Physician(s) of Record | anon
(0010, 0040) Patient's Sex | anon
(0010, 1010) Patient's Age | anon
(0009, 1002) Private tag data | anon
(0010, 1000) Other Patient IDs | anon
(0008, 1070) Operators' Name | anon
(0011, 0010) Private Creator | anon
(0010, 0020) Patient ID | anon
(0011, 1001) Private tag data | anon
(0008, 0050) Accession Number | anon
(0008, 0090) Referring Physician's Name | anon
(0008, 1040) Institutional Department Name | anon
(0010, 0010) Patient's Name | anon
(0010, 1001) Other Patient Names | anon
(0008, 0020) Study Date | date
(0008, 0021) Series Date | date
(0008, 0022) Acquisition Date | date
(0010, 0030) Patient's Birth Date | date
(0008, 0030) Study Time | time
(0008, 0032) Acquisition Time | time
(0008, 0031) Series Time | time
"""


# -- Create TK -- 
root = tk.Tk()
root.title("DICOM 去識別")

# --- Directory selectors ---
dir_vars = [tk.StringVar(value="No directory selected") for _ in range(2)]

for i in range(2):
    frame = tk.Frame(root)
    frame.pack(fill='x', pady=2)
    btn = tk.Button(frame, text=f"Select Directory {i+1}", command=lambda idx=i: select_directory(idx))
    btn.pack(side='left')
    lbl = tk.Label(frame, textvariable=dir_vars[i], width=50, anchor='w')
    lbl.pack(side='left', padx=5)


# --- Checkboxes ---
checkbox_info = []

lines = DICOM_TAGS.split("\n")
for line in lines:
    line = line.strip()
    if len(line) == 0:
        continue
    if line.find("|") < 0:
        continue
    fulltag = line
    desc, _ = line.split(" | ")
    desc = desc.strip()
    checkbox_info.append((desc, fulltag.strip()))

checkbox_frame = tk.Frame(root)
checkbox_frame.pack(pady=(0,6))
checkboxes = {}

# Place checkboxes in two columns, 5 per column
for idx, (key, label) in enumerate(checkbox_info):
    checkbox_per_col = 10
    var = tk.BooleanVar()
    col = idx // checkbox_per_col   # 0 or 1
    row = idx % checkbox_per_col
    chk = tk.Checkbutton(checkbox_frame, text=label, variable=var, command=lambda k=key: on_checkbox_toggle(k))
    chk.grid(row=row, column=col, sticky='w', padx=10, pady=2)
    checkboxes[key] = (var, label)


# --- Progress bar ---
progress_bar = ttk.Progressbar(root, orient='horizontal', length=500, mode='indeterminate')
progress_bar.pack(pady=6)

btn = tk.Button(root, text="Anonymize!", command=start_anonymize)
btn.pack(pady=10)

# --- Logging window ---
log_label = tk.Label(root, text="Log Output:")
log_label.pack(anchor='w')
log_text = ScrolledText(root, height=7, width=70, state='disabled', font=("consolas", 9))
log_text.pack(padx=5, pady=(0,8), fill='both', expand=False)

root.mainloop()