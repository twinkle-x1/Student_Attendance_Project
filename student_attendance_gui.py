import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import ctypes
from ctypes import wintypes

APP_DIR = Path(__file__).resolve().parent
JAR_PATH = APP_DIR / "lib" / "ojdbc17-23.26.4.0.0.jar"
JAVA_FILE = APP_DIR / "AttendanceBridge.java"
CLASS_FILE = APP_DIR / "AttendanceBridge.class"

CREDENTIAL_TARGET = "StudentAttendanceDashboard/OracleFreeSQL"
ORACLE_USERNAME = "TWI1975RMA_SCHEMA_R6I35"
oracle_password = ""


# Windows Credential Manager: the password is stored encrypted by Windows,
# not in this Python file or the Java source.
class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD),
                ("dwHighDateTime", wintypes.DWORD)]

class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]

def credential_api():
    advapi = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    advapi.CredReadW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.POINTER(CREDENTIAL))
    ]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredWriteW.argtypes = [
        ctypes.POINTER(CREDENTIAL), wintypes.DWORD
    ]
    advapi.CredWriteW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    advapi.CredFree.restype = None
    return advapi

def load_saved_password():
    advapi = credential_api()
    pointer = ctypes.POINTER(CREDENTIAL)()
    if not advapi.CredReadW(CREDENTIAL_TARGET, 1, 0, ctypes.byref(pointer)):
        return ""
    try:
        item = pointer.contents
        raw = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
        return raw.decode("utf-8")
    finally:
        advapi.CredFree(pointer)

def store_password(password):
    advapi = credential_api()
    encoded = password.encode("utf-8")
    blob = ctypes.create_string_buffer(encoded)
    item = CREDENTIAL()
    item.Flags = 0
    item.Type = 1  # CRED_TYPE_GENERIC
    item.TargetName = CREDENTIAL_TARGET
    item.Comment = "Student Attendance Dashboard Oracle login"
    item.CredentialBlobSize = len(encoded)
    item.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))
    item.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
    item.AttributeCount = 0
    item.Attributes = None
    item.TargetAlias = None
    item.UserName = ORACLE_USERNAME
    if not advapi.CredWriteW(ctypes.byref(item), 0):
        raise ctypes.WinError(ctypes.get_last_error())

def request_and_save_password():
    global oracle_password
    value = simpledialog.askstring(
        "First-time Oracle setup",
        "Enter your Oracle FreeSQL password once.\n"
        "Windows will store it securely for future launches:",
        show="*",
        parent=root
    )
    if not value:
        return False
    try:
        store_password(value)
        oracle_password = value
        password_state.config(
            text="Oracle login saved securely in Windows. No repeated entry needed.",
            fg="#15803d"
        )
        return True
    except Exception as exc:
        messagebox.showerror(
            "Secure storage error",
            f"Could not save the password in Windows Credential Manager:\n{exc}"
        )
        return False

def reset_saved_password():
    if request_and_save_password():
        messagebox.showinfo("Login saved", "The saved Oracle login has been updated.")

def compile_java_helper():
    if not JAR_PATH.exists():
        messagebox.showerror(
            "JDBC driver not found",
            f"Place ojdbc17-23.26.4.0.0.jar inside:\n{APP_DIR / 'lib'}"
        )
        return False
    if not JAVA_FILE.exists():
        messagebox.showerror("Missing file", "AttendanceBridge.java is missing.")
        return False
    needs_compile = (
        not CLASS_FILE.exists()
        or CLASS_FILE.stat().st_mtime < JAVA_FILE.stat().st_mtime
    )
    if needs_compile:
        result = subprocess.run(
            ["javac", "-cp", f".;{JAR_PATH}", str(JAVA_FILE)],
            cwd=APP_DIR, capture_output=True, text=True
        )
        if result.returncode != 0:
            messagebox.showerror(
                "Java compilation error",
                result.stderr or result.stdout or "Compilation failed."
            )
            return False
    return True

def run_bridge(input_text):
    if not compile_java_helper():
        return None
    try:
        result = subprocess.run(
            ["java", "-cp", f".;{JAR_PATH}", "AttendanceBridge"],
            input=input_text, capture_output=True, text=True,
            cwd=APP_DIR, timeout=60
        )
    except subprocess.TimeoutExpired:
        messagebox.showerror("Timeout", "Oracle did not respond in time.")
        return None
    lines = result.stdout.strip().splitlines()
    if not lines:
        messagebox.showerror(
            "Java error",
            result.stderr.strip() or "No response received from the database helper."
        )
        return None
    if lines[0] == "ERROR":
        messagebox.showerror(
            "Database error",
            lines[1] if len(lines) > 1 else "Unknown database error."
        )
        return None
    if lines[0] != "SUCCESS":
        messagebox.showerror("Unexpected response", result.stdout)
        return None
    return lines

def set_metric(label, value):
    label.config(text=str(value))

def refresh_dashboard():
    if not oracle_password:
        messagebox.showwarning(
            "Oracle login not set",
            "Use 'Save / Change Login' once to securely save your Oracle password."
        )
        return
    refresh_button.config(state="disabled")
    root.update_idletasks()
    lines = run_bridge(f"DASHBOARD\n{oracle_password}\n")
    refresh_button.config(state="normal")
    if lines is None:
        return
    if len(lines) < 6 or lines[1] != "DASHBOARD":
        messagebox.showerror("Invalid response", "The dashboard response was incomplete.")
        return
    try:
        set_metric(total_students_value, lines[2])
        set_metric(total_records_value, lines[3])
        set_metric(shortage_students_value, lines[4])
        set_metric(safe_students_value, lines[5])
        for item in table.get_children():
            table.delete(item)
        count = 0
        for row in lines[6:]:
            parts = row.split("\t")
            if len(parts) != 7:
                continue
            roll, name, subject, total, attended, percentage, status = parts
            tag = "shortage" if status == "SHORTAGE ALERT" else "safe"
            table.insert(
                "", "end",
                values=(roll, name, subject, total, attended,
                        f"{percentage}%", status),
                tags=(tag,)
            )
            count += 1
        dashboard_state.config(
            text=f"Dashboard updated successfully. Showing {count} student-subject records.",
            fg="#15803d"
        )
        apply_filter()
    except (ValueError, IndexError) as error:
        messagebox.showerror("Display error", str(error))

def check_one_student():
    roll = check_roll_entry.get().strip()
    subject = check_subject_entry.get().strip()
    if not roll or not subject:
        messagebox.showwarning("Missing details", "Enter both roll number and subject name.")
        return
    if not oracle_password:
        messagebox.showwarning("Oracle login not set", "Save your Oracle login first.")
        return
    lines = run_bridge(f"CHECK\n{oracle_password}\n{roll}\n{subject}\n")
    if lines is None:
        return
    if len(lines) < 6 or lines[1] != "CHECK":
        messagebox.showerror("Invalid response", "Could not read the attendance result.")
        return
    total, attended, percentage, status = lines[2:6]
    check_total_value.config(text=f"Total classes: {total}")
    check_attended_value.config(text=f"Attended: {attended}")
    check_percentage_value.config(text=f"Attendance: {float(percentage):.2f}%")
    check_status_value.config(
        text=status,
        fg="#b91c1c" if status == "SHORTAGE ALERT"
        else "#15803d" if status == "SAFE" else "#b45309"
    )

def apply_filter(*_):
    search = search_var.get().strip().lower()
    selected = status_filter.get()
    for item in table.get_children():
        values = table.item(item, "values")
        text = " ".join(str(value) for value in values).lower()
        status = str(values[6])
        search_match = search in text
        status_match = (
            selected == "All"
            or (selected == "Shortage Alert" and status == "SHORTAGE ALERT")
            or (selected == "Safe" and status == "SAFE")
        )
        if search_match and status_match:
            table.reattach(item, "", "end")
        else:
            table.detach(item)

def clear_search():
    search_var.set("")
    status_filter.set("All")
    apply_filter()

root = tk.Tk()
root.title("Student Attendance Shortage Alert System")
root.geometry("1450x900")
root.minsize(1050, 760)
root.configure(bg="#f1f5f9")

style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass
style.configure("Treeview", font=("Segoe UI", 9), rowheight=25)
style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6)
style.configure("TEntry", padding=5)

header = tk.Frame(root, bg="#17324d", padx=22, pady=12)
header.pack(fill="x")
tk.Label(
    header, text="STUDENT ATTENDANCE DASHBOARD",
    font=("Segoe UI", 18, "bold"), bg="#17324d", fg="white"
).pack(anchor="w")
tk.Label(
    header, text="Attendance monitoring and shortage alert system",
    font=("Segoe UI", 9), bg="#17324d", fg="#cbd5e1"
).pack(anchor="w", pady=(2, 0))

main = tk.Frame(root, bg="#f1f5f9", padx=16, pady=9)
main.pack(fill="both", expand=True)

login = tk.LabelFrame(
    main, text="Oracle FreeSQL Connection",
    font=("Segoe UI", 9, "bold"), bg="#f1f5f9",
    fg="#17324d", padx=10, pady=6
)
login.pack(fill="x", pady=(0, 8))
password_state = tk.Label(
    login, text="Checking Windows Credential Manager...",
    bg="#f1f5f9", fg="#64748b", font=("Segoe UI", 9)
)
password_state.pack(side="left", padx=4)
ttk.Button(
    login, text="Save / Change Login", command=reset_saved_password
).pack(side="right", padx=4)

metrics = tk.Frame(main, bg="#f1f5f9")
metrics.pack(fill="x", pady=(0, 8))

def metric_card(parent, title, color):
    card = tk.Frame(
        parent, bg="white", padx=12, pady=8,
        highlightbackground="#cbd5e1", highlightthickness=1
    )
    card.pack(side="left", fill="both", expand=True, padx=4)
    tk.Label(
        card, text=title, bg="white", fg="#64748b",
        font=("Segoe UI", 9, "bold")
    ).pack(anchor="w")
    value = tk.Label(
        card, text="—", bg="white", fg=color,
        font=("Segoe UI", 20, "bold")
    )
    value.pack(anchor="w", pady=(3, 0))
    return value

total_students_value = metric_card(metrics, "TOTAL STUDENTS", "#17324d")
total_records_value = metric_card(metrics, "ATTENDANCE RECORDS", "#2563eb")
shortage_students_value = metric_card(metrics, "STUDENTS WITH SHORTAGE", "#b91c1c")
safe_students_value = metric_card(metrics, "STUDENTS WITH NO SHORTAGE", "#15803d")

dashboard_bar = tk.Frame(main, bg="#f1f5f9")
dashboard_bar.pack(fill="x", pady=(0, 5))
tk.Label(
    dashboard_bar, text="Subject-wise Attendance Records",
    bg="#f1f5f9", fg="#17324d", font=("Segoe UI", 11, "bold")
).pack(side="left")
refresh_button = ttk.Button(
    dashboard_bar, text="Refresh Dashboard", command=refresh_dashboard
)
refresh_button.pack(side="right")

filters = tk.Frame(main, bg="#f1f5f9")
filters.pack(fill="x", pady=(0, 6))
tk.Label(filters, text="Search:", bg="#f1f5f9", fg="#334155").pack(side="left")
search_var = tk.StringVar()
search_var.trace_add("write", apply_filter)
ttk.Entry(filters, textvariable=search_var, width=28).pack(side="left", padx=(6, 14))
tk.Label(filters, text="Status:", bg="#f1f5f9", fg="#334155").pack(side="left")
status_filter = tk.StringVar(value="All")
status_box = ttk.Combobox(
    filters, textvariable=status_filter,
    values=("All", "Shortage Alert", "Safe"),
    state="readonly", width=17
)
status_box.pack(side="left", padx=6)
status_box.bind("<<ComboboxSelected>>", apply_filter)
ttk.Button(filters, text="Clear Filters", command=clear_search).pack(side="left", padx=6)

table_frame = tk.Frame(main, bg="white")
table_frame.pack(fill="both", expand=True, pady=(0, 5))
columns = ("roll", "name", "subject", "total", "attended", "percentage", "status")
table = ttk.Treeview(table_frame, columns=columns, show="headings", height=7)
headings = {
    "roll": "Roll No", "name": "Student Name", "subject": "Subject",
    "total": "Total Classes", "attended": "Attended",
    "percentage": "Percentage", "status": "Status"
}
widths = {
    "roll": 100, "name": 190, "subject": 170,
    "total": 110, "attended": 100, "percentage": 110, "status": 170
}
for col in columns:
    table.heading(col, text=headings[col])
    table.column(col, width=widths[col], anchor="center")
table.tag_configure("shortage", foreground="#b91c1c")
table.tag_configure("safe", foreground="#15803d")
scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
table.grid(row=0, column=0, sticky="nsew")
scroll_y.grid(row=0, column=1, sticky="ns")
scroll_x.grid(row=1, column=0, sticky="ew")
table_frame.rowconfigure(0, weight=1)
table_frame.columnconfigure(0, weight=1)

dashboard_state = tk.Label(
    main, text="Dashboard will show after connecting to Oracle.",
    bg="#f1f5f9", fg="#64748b", font=("Segoe UI", 9)
)
dashboard_state.pack(anchor="w", pady=(2, 5))

# The individual check area now uses two clear rows so no labels or values
# are clipped at the bottom of the window.
check_frame = tk.LabelFrame(
    main, text="Individual Attendance Check",
    font=("Segoe UI", 9, "bold"), bg="#f1f5f9",
    fg="#17324d", padx=10, pady=7
)
check_frame.pack(fill="x", pady=(0, 4))

input_row = tk.Frame(check_frame, bg="#f1f5f9")
input_row.pack(fill="x", anchor="w")
tk.Label(input_row, text="Roll Number", bg="#f1f5f9", fg="#334155").pack(side="left")
check_roll_entry = ttk.Entry(input_row, width=18)
check_roll_entry.pack(side="left", padx=(6, 14))
check_roll_entry.insert(0, "MCA105")
tk.Label(input_row, text="Subject", bg="#f1f5f9", fg="#334155").pack(side="left")
check_subject_entry = ttk.Entry(input_row, width=18)
check_subject_entry.pack(side="left", padx=(6, 12))
check_subject_entry.insert(0, "AIP")
ttk.Button(input_row, text="Check Attendance", command=check_one_student).pack(side="left")

result_row = tk.Frame(check_frame, bg="#f1f5f9")
result_row.pack(fill="x", anchor="w", pady=(7, 0))
check_total_value = tk.Label(
    result_row, text="Total classes: —", bg="#f1f5f9", fg="#334155",
    font=("Segoe UI", 9, "bold")
)
check_total_value.pack(side="left", padx=(0, 22))
check_attended_value = tk.Label(
    result_row, text="Attended: —", bg="#f1f5f9", fg="#334155",
    font=("Segoe UI", 9, "bold")
)
check_attended_value.pack(side="left", padx=(0, 22))
check_percentage_value = tk.Label(
    result_row, text="Attendance: —", bg="#f1f5f9", fg="#334155",
    font=("Segoe UI", 9, "bold")
)
check_percentage_value.pack(side="left", padx=(0, 22))
check_status_value = tk.Label(
    result_row, text="Status: —", bg="#f1f5f9",
    fg="#334155", font=("Segoe UI", 9, "bold")
)
check_status_value.pack(side="left")

footer = tk.Label(
    root,
    text="Python Tkinter  |  Java JDBC  |  Oracle FreeSQL  |  PL/SQL",
    bg="#e2e8f0", fg="#475569", font=("Segoe UI", 8), pady=5
)
footer.pack(fill="x")

# Load the saved Windows credential. Only the first launch asks for it.
try:
    oracle_password = load_saved_password()
    if oracle_password:
        password_state.config(
            text="Oracle login loaded securely from Windows Credential Manager.",
            fg="#15803d"
        )
    else:
        password_state.config(
            text="First run: click 'Save / Change Login' once to save your Oracle password.",
            fg="#b45309"
        )
        root.after(400, request_and_save_password)
except Exception as exc:
    password_state.config(
        text="Windows secure password storage is unavailable.",
        fg="#b91c1c"
    )
    root.after(
        500,
        lambda: messagebox.showerror(
            "Credential Manager error",
            f"Could not access Windows Credential Manager:\n{exc}"
        )
    )

root.mainloop()
