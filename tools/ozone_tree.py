import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

BASE_URI = "ofs://om/s3v/warehouse"

DOCKER_CMD = [
    "docker", "compose",
    "-f", "docker-compose.yaml",
    "-f", "iceberg-spark.yml",
    "-f", "trino.yml",
    "exec", "-T", "s3g",
    "ozone", "fs", "-ls", "-R",
    BASE_URI
]


def get_ozone_tree():
    result = subprocess.run(
        DOCKER_CMD,
        capture_output=True,
        text=True,
        check=True
    )

    tree = {}

    for line in result.stdout.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if len(parts) < 8:
            continue

        permissions = parts[0]
        size = parts[4]
        path = parts[-1]

        if not path.startswith(BASE_URI):
            continue

        relative_path = path[len(BASE_URI):].strip("/")

        if not relative_path:
            continue

        path_parts = relative_path.split("/")

        current = tree

        for i, part in enumerate(path_parts):
            if part not in current:
                current[part] = {
                    "__children__": {},
                    "__type__": "folder",
                    "__size__": ""
                }

            # Last component = actual object returned by ls
            if i == len(path_parts) - 1:
                current[part]["__type__"] = (
                    "folder" if permissions.startswith("d") else "file"
                )

                if not permissions.startswith("d"):
                    current[part]["__size__"] = size

            current = current[part]["__children__"]

    return tree


def human_size(size):
    try:
        size = int(size)
    except:
        return ""

    units = ["B", "KB", "MB", "GB", "TB"]

    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} PB"


def insert_nodes(parent, nodes):
    # Folder first, then file
    sorted_nodes = sorted(
        nodes.items(),
        key=lambda x: (
            x[1]["__type__"] != "folder",
            x[0].lower()
        )
    )

    for name, info in sorted_nodes:

        if info["__type__"] == "folder":
            icon = "📁"
            size = ""
            obj_type = "Folder"
        else:
            icon = "📄"
            size = human_size(info["__size__"])
            obj_type = "File"

        item_id = treeview.insert(
            parent,
            "end",
            text=f"{icon} {name}",
            values=(obj_type, size),
            open=False
        )

        insert_nodes(
            item_id,
            info["__children__"]
        )


def refresh():
    refresh_button.config(state="disabled")
    status_var.set("Loading Ozone namespace...")
    root.update_idletasks()

    try:
        data = get_ozone_tree()

        # Clear current tree
        for item in treeview.get_children():
            treeview.delete(item)

        root_node = treeview.insert(
            "",
            "end",
            text="📁 warehouse",
            values=("Folder", ""),
            open=True
        )

        insert_nodes(root_node, data)

        status_var.set("Loaded successfully.")

    except subprocess.CalledProcessError as e:
        status_var.set("Failed.")

        messagebox.showerror(
            "Ozone error",
            e.stderr or str(e)
        )

    except Exception as e:
        status_var.set("Failed.")

        messagebox.showerror(
            "Error",
            str(e)
        )

    finally:
        refresh_button.config(state="normal")


# ========================
# GUI
# ========================

root = tk.Tk()
root.title("Apache Ozone Warehouse Explorer")
root.geometry("1050x700")

ada = 0.8
FONT_NORMAL = int(14 * ada)
FONT_TITLE = int(20 * ada)

root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")

style.configure(
    ".",
    font=("Segoe UI", FONT_NORMAL),
    background="#1e1e1e",
    foreground="white",
    fieldbackground="#1e1e1e"
)

style.configure(
    "Treeview",
    font=("Segoe UI", FONT_NORMAL),
    rowheight=40,
    background="#1e1e1e",
    foreground="white",
    fieldbackground="#1e1e1e"
)

style.configure(
    "Treeview.Heading",
    font=("Segoe UI", FONT_NORMAL, "bold"),
    background="#2d2d2d",
    foreground="white"
)

style.map(
    "Treeview",
    background=[("selected", "#404040")],
    foreground=[("selected", "white")]
)

main_frame = ttk.Frame(root, padding=10)
main_frame.pack(fill="both", expand=True)


# ---------- Top ----------
top_frame = ttk.Frame(main_frame)
top_frame.pack(fill="x", pady=(0, 10))

title = ttk.Label(
    top_frame,
    text="Apache Ozone Warehouse Explorer",
    font=("Segoe UI", FONT_TITLE, "bold")
)
title.pack(side="left")

refresh_button = ttk.Button(
    top_frame,
    text="Refresh",
    command=refresh
)
refresh_button.pack(side="right")


# ---------- Path ----------
path_frame = ttk.Frame(main_frame)
path_frame.pack(fill="x", pady=(0, 10))

ttk.Label(
    path_frame,
    text="Ozone path:"
).pack(side="left")

path_label = ttk.Label(
    path_frame,
    text=BASE_URI,
    font=("Consolas", FONT_NORMAL)
)
path_label.pack(side="left", padx=10)


# ---------- Tree ----------
tree_frame = ttk.Frame(main_frame)
tree_frame.pack(fill="both", expand=True)

treeview = ttk.Treeview(
    tree_frame,
    columns=("type", "size")
)

treeview.heading("#0", text="Name")
treeview.heading("type", text="Type")
treeview.heading("size", text="Size")

treeview.column("#0", width=700)
treeview.column("type", width=100, anchor="center")
treeview.column("size", width=120, anchor="e")

scroll_y = ttk.Scrollbar(
    tree_frame,
    orient="vertical",
    command=treeview.yview
)

scroll_x = ttk.Scrollbar(
    tree_frame,
    orient="horizontal",
    command=treeview.xview
)

treeview.configure(
    yscrollcommand=scroll_y.set,
    xscrollcommand=scroll_x.set
)

treeview.grid(
    row=0,
    column=0,
    sticky="nsew"
)

scroll_y.grid(
    row=0,
    column=1,
    sticky="ns"
)

scroll_x.grid(
    row=1,
    column=0,
    sticky="ew"
)

tree_frame.rowconfigure(0, weight=1)
tree_frame.columnconfigure(0, weight=1)


# ---------- Status ----------
status_var = tk.StringVar(
    value="Ready."
)

status_label = ttk.Label(
    main_frame,
    textvariable=status_var
)
status_label.pack(fill="x", pady=(8, 0))


# Load automatically when opened
root.after(100, refresh)

root.mainloop()