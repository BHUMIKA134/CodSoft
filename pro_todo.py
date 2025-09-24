#!/usr/bin/env python3
"""
Pro To-Do — A distinctive, internship-ready Tkinter + SQLite to-do app.
Features:
- SQLite persistence, schema migration
- Priority (High/Medium/Low) with colored rows
- Due date (YYYY-MM-DD), smart sorting (Priority->Due->Created)
- Search, filters (priority/status), live refresh
- Keyboard shortcuts: Ctrl+N (new), Ctrl+E (edit), Ctrl+D (toggle done), Ctrl+F (focus search), Delete (remove)
- Right-click context menu
- Undo last delete
- JSON import/export (no third-party libs)
"""

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

DB_PATH = Path("todo_pro.sqlite3")

# ---------- Domain model ----------
@dataclass
class Task:
    id: int | None
    title: str
    notes: str
    priority: str           # "High" | "Medium" | "Low"
    due_date: str | None    # "YYYY-MM-DD" or None
    done: int               # 0 or 1
    created_at: str
    updated_at: str

PRIORITIES = ["High", "Medium", "Low"]

def iso_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def valid_date_or_none(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")

# ---------- Repository layer ----------
class TaskRepo:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self._migrate()

    def _migrate(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL CHECK (priority IN ('High','Medium','Low')) DEFAULT 'Medium',
                due_date TEXT,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        # Add columns if missing (safe idempotent migrations)
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(tasks)")}
        if "notes" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN notes TEXT NOT NULL DEFAULT '';")
        if "priority" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'Medium';")
        if "due_date" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT;")
        if "done" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN done INTEGER NOT NULL DEFAULT 0;")
        if "created_at" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT NOT NULL DEFAULT '';")
        if "updated_at" not in cols:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT NOT NULL DEFAULT '';")
        self.conn.commit()

    # CRUD
    def create(self, title: str, notes: str, priority: str, due_date: str | None) -> int:
        now = iso_now()
        cur = self.conn.execute(
            "INSERT INTO tasks(title,notes,priority,due_date,done,created_at,updated_at) VALUES (?,?,?,?,0,?,?)",
            (title, notes, priority, due_date, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def update(self, task_id: int, title: str, notes: str, priority: str, due_date: str | None):
        now = iso_now()
        self.conn.execute(
            "UPDATE tasks SET title=?, notes=?, priority=?, due_date=?, updated_at=? WHERE id=?",
            (title, notes, priority, due_date, now, task_id),
        )
        self.conn.commit()

    def toggle_done(self, task_id: int):
        self.conn.execute(
            "UPDATE tasks SET done = CASE done WHEN 1 THEN 0 ELSE 1 END, updated_at=? WHERE id=?",
            (iso_now(), task_id),
        )
        self.conn.commit()

    def delete(self, task_id: int) -> Task | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            return None
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()
        return Task(**row)

    def get(self, task_id: int) -> Task | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return Task(**row) if row else None

    def list(self, q: str = "", priority: str = "All", status: str = "All") -> list[Task]:
        clauses = []
        args: list = []
        if q:
            clauses.append("(title LIKE ? OR notes LIKE ?)")
            like = f"%{q}%"
            args += [like, like]
        if priority in PRIORITIES:
            clauses.append("priority = ?")
            args.append(priority)
        if status == "Pending":
            clauses.append("done = 0")
        elif status == "Done":
            clauses.append("done = 1")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # Smart order: High->Med->Low, due date NULLs last, then created_at
        sql = f"""
        SELECT * FROM tasks
        {where}
        ORDER BY 
          CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
          CASE WHEN due_date IS NULL OR due_date='' THEN 1 ELSE 0 END,
          due_date ASC,
          created_at ASC
        """
        rows = self.conn.execute(sql, args).fetchall()
        return [Task(**r) for r in rows]

    # Export/Import
    def export_json(self, path: Path):
        data = [t.__dict__ for t in self.list()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_json(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        for it in items:
            title = it.get("title") or "(untitled)"
            notes = it.get("notes", "")
            priority = it.get("priority", "Medium")
            if priority not in PRIORITIES:
                priority = "Medium"
            due_date = it.get("due_date") or None
            try:
                due_date = valid_date_or_none(due_date)
            except ValueError:
                due_date = None
            self.create(title, notes, priority, due_date)

# ---------- UI helpers ----------
class TaskDialog(simpledialog.Dialog):
    def __init__(self, parent, title: str, initial: Task | None = None):
        self.initial = initial
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Title *").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.title_var = tk.StringVar(value=self.initial.title if self.initial else "")
        self.title_entry = ttk.Entry(master, textvariable=self.title_var, width=48)
        self.title_entry.grid(row=0, column=1, padx=4, pady=4)

        ttk.Label(master, text="Notes").grid(row=1, column=0, sticky="nw", padx=4, pady=4)
        self.notes = tk.Text(master, width=48, height=6)
        if self.initial:
            self.notes.insert("1.0", self.initial.notes)
        self.notes.grid(row=1, column=1, padx=4, pady=4)

        ttk.Label(master, text="Priority").grid(row=2, column=0, sticky="w", padx=4, pady=4)
        self.priority_var = tk.StringVar(value=self.initial.priority if self.initial else "Medium")
        self.priority_cb = ttk.Combobox(master, values=PRIORITIES, textvariable=self.priority_var, state="readonly", width=12)
        self.priority_cb.grid(row=2, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(master, text="Due (YYYY-MM-DD)").grid(row=3, column=0, sticky="w", padx=4, pady=4)
        self.due_var = tk.StringVar(value=self.initial.due_date if (self.initial and self.initial.due_date) else "")
        self.due_entry = ttk.Entry(master, textvariable=self.due_var, width=16)
        self.due_entry.grid(row=3, column=1, sticky="w", padx=4, pady=4)

        return self.title_entry

    def validate(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Validation", "Title is required.")
            return False
        due = self.due_var.get().strip()
        if due:
            try:
                valid_date_or_none(due)
            except ValueError as e:
                messagebox.showwarning("Validation", str(e))
                return False
        return True

    def apply(self):
        self.result = {
            "title": self.title_var.get().strip(),
            "notes": self.notes.get("1.0", "end-1c"),
            "priority": self.priority_var.get(),
            "due_date": self.due_var.get().strip() or None,
        }

# ---------- Main App ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My To-Do List")
        self.geometry("900x560")
        self.minsize(780, 480)

        self.repo = TaskRepo(DB_PATH)
        self.deleted_stack: list[Task] = []

        self._build_style()
        self._build_toolbar()
        self._build_table()
        self._build_statusbar()
        self._bind_shortcuts()
        self.refresh()

    # UI construction
    def _build_style(self):
        style = ttk.Style(self)
        # Use system theme where possible
        theme = "vista" if "vista" in style.theme_names() else ("clam" if "clam" in style.theme_names() else style.theme_use())
        style.theme_use(theme)
        style.configure("Treeview", rowheight=26)
        style.configure("TButton", padding=6)
        style.configure("TEntry", padding=4)

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(8, 6))
        bar.pack(side="top", fill="x")

        # Search
        ttk.Label(bar, text="Search").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="left", padx=(6, 12))
        self.search_var.trace_add("write", lambda *_: self.refresh())

        # Priority filter
        ttk.Label(bar, text="Priority").pack(side="left")
        self.priority_filter = tk.StringVar(value="All")
        ttk.Combobox(bar, values=["All"] + PRIORITIES, textvariable=self.priority_filter, state="readonly", width=10)\
            .pack(side="left", padx=(6, 12))
        self.priority_filter.trace_add("write", lambda *_: self.refresh())

        # Status filter
        ttk.Label(bar, text="Status").pack(side="left")
        self.status_filter = tk.StringVar(value="All")
        ttk.Combobox(bar, values=["All", "Pending", "Done"], textvariable=self.status_filter, state="readonly", width=10)\
            .pack(side="left", padx=(6, 12))
        self.status_filter.trace_add("write", lambda *_: self.refresh())

        # Buttons
        btns = ttk.Frame(bar)
        btns.pack(side="right")
        ttk.Button(btns, text="New (Ctrl+N)", command=self.on_new).pack(side="left", padx=4)
        ttk.Button(btns, text="Edit (Ctrl+E)", command=self.on_edit).pack(side="left", padx=4)
        ttk.Button(btns, text="Toggle Done (Ctrl+D)", command=self.on_toggle).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete (Del)", command=self.on_delete).pack(side="left", padx=4)
        ttk.Button(btns, text="Undo Delete", command=self.on_undo).pack(side="left", padx=4)
        ttk.Button(btns, text="Export", command=self.on_export).pack(side="left", padx=4)
        ttk.Button(btns, text="Import", command=self.on_import).pack(side="left", padx=4)

    def _build_table(self):
        container = ttk.Frame(self, padding=(8, 0, 8, 8))
        container.pack(fill="both", expand=True)

        cols = ("title", "priority", "due_date", "done", "updated_at")
        self.tree = ttk.Treeview(container, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("title", text="Task")
        self.tree.heading("priority", text="Priority")
        self.tree.heading("due_date", text="Due")
        self.tree.heading("done", text="Status")
        self.tree.heading("updated_at", text="Updated")

        self.tree.column("title", width=420, anchor="w")
        self.tree.column("priority", width=90, anchor="center")
        self.tree.column("due_date", width=100, anchor="center")
        self.tree.column("done", width=90, anchor="center")
        self.tree.column("updated_at", width=160, anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Context menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="New", command=self.on_new)
        self.menu.add_command(label="Edit", command=self.on_edit)
        self.menu.add_command(label="Toggle Done", command=self.on_toggle)
        self.menu.add_separator()
        self.menu.add_command(label="Delete", command=self.on_delete)
        self.menu.add_command(label="Undo Delete", command=self.on_undo)

        self.tree.bind("<Button-3>", self._popup)
        self.tree.bind("<Double-1>", lambda e: self.on_edit())

    def _build_statusbar(self):
        self.status = tk.StringVar(value="Ready.")
        bar = ttk.Frame(self, relief="sunken")
        bar.pack(side="bottom", fill="x")
        ttk.Label(bar, textvariable=self.status, anchor="w", padding=(8, 4)).pack(fill="x")

    # Shortcuts
    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.on_new())
        self.bind("<Control-N>", lambda e: self.on_new())
        self.bind("<Control-e>", lambda e: self.on_edit())
        self.bind("<Control-E>", lambda e: self.on_edit())
        self.bind("<Control-d>", lambda e: self.on_toggle())
        self.bind("<Control-D>", lambda e: self.on_toggle())
        self.bind("<Delete>", lambda e: self.on_delete())
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())
        self.bind("<Control-F>", lambda e: self.search_entry.focus_set())

    # Actions
    def selected_id(self) -> int | None:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def on_new(self):
        dlg = TaskDialog(self, "New Task")
        if not dlg.result:
            return
        data = dlg.result
        try:
            due = valid_date_or_none(data["due_date"])
        except ValueError as e:
            messagebox.showwarning("Invalid date", str(e))
            return
        new_id = self.repo.create(data["title"], data["notes"], data["priority"], due)
        self.status.set(f"Created task #{new_id}.")
        self.refresh(select_id=new_id)

    def on_edit(self):
        tid = self.selected_id()
        if not tid:
            messagebox.showinfo("Edit", "Select a task to edit.")
            return
        current = self.repo.get(tid)
        if not current:
            return
        dlg = TaskDialog(self, "Edit Task", initial=current)
        if not dlg.result:
            return
        data = dlg.result
        try:
            due = valid_date_or_none(data["due_date"])
        except ValueError as e:
            messagebox.showwarning("Invalid date", str(e))
            return
        self.repo.update(tid, data["title"], data["notes"], data["priority"], due)
        self.status.set(f"Updated task #{tid}.")
        self.refresh(select_id=tid)

    def on_toggle(self):
        tid = self.selected_id()
        if not tid:
            messagebox.showinfo("Toggle Done", "Select a task to toggle status.")
            return
        self.repo.toggle_done(tid)
        t = self.repo.get(tid)
        state = "Done" if (t and t.done) else "Pending"
        self.status.set(f"Toggled task #{tid} → {state}.")
        self.refresh(select_id=tid)

    def on_delete(self):
        tid = self.selected_id()
        if not tid:
            messagebox.showinfo("Delete", "Select a task to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected task?"):
            return
        snapshot = self.repo.delete(tid)
        if snapshot:
            self.deleted_stack.append(snapshot)
        self.status.set(f"Deleted task #{tid}. You can Undo.")
        self.refresh()

    def on_undo(self):
        if not self.deleted_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        t = self.deleted_stack.pop()
        # Recreate (as new id)
        new_id = self.repo.create(t.title, t.notes, t.priority, t.due_date)
        self.status.set(f"Restored task as #{new_id}.")
        self.refresh(select_id=new_id)

    def on_export(self):
        path = filedialog.asksaveasfilename(
            title="Export to JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        if not path:
            return
        self.repo.export_json(Path(path))
        self.status.set(f"Exported to {path}.")

    def on_import(self):
        path = filedialog.askopenfilename(
            title="Import from JSON",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        self.repo.import_json(Path(path))
        self.status.set(f"Imported tasks from {path}.")
        self.refresh()

    def _popup(self, event):
        try:
            row = self.tree.identify_row(event.y)
            if row:
                self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # Refresh & paint
    def refresh(self, select_id: int | None = None):
        q = self.search_var.get().strip()
        pf = self.priority_filter.get()
        sf = self.status_filter.get()

        tasks = self.repo.list(q=q, priority=pf, status=sf)

        # Clear
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # Insert with colored tags
        for t in tasks:
            done_label = "✔ Done" if t.done else "⏳ Pending"
            iid = str(t.id)
            self.tree.insert("", "end", iid=iid, values=(t.title, t.priority, t.due_date or "-", done_label, t.updated_at))
            # Color by priority & strike-through effect for done
            if t.priority == "High":
                self.tree.tag_configure("p_high", foreground="#c62828")
                self.tree.item(iid, tags=("p_high",))
            elif t.priority == "Medium":
                self.tree.tag_configure("p_med", foreground="#6a1b9a")
                self.tree.item(iid, tags=("p_med",))
            else:
                self.tree.tag_configure("p_low", foreground="#2e7d32")
                self.tree.item(iid, tags=("p_low",))
            if t.done:
                # soften text to indicate completion
                self.tree.tag_configure("done_dim", foreground="#777777")
                tags = list(self.tree.item(iid, "tags"))
                tags.append("done_dim")
                self.tree.item(iid, tags=tuple(tags))

        if select_id:
            sid = str(select_id)
            if sid in self.tree.get_children(""):
                self.tree.selection_set(sid)
                self.tree.see(sid)

        total = len(tasks)
        pending = sum(1 for t in tasks if not t.done)
        self.status.set(f"{total} shown | {pending} pending | Filters: Priority={pf}, Status={sf}")

# ---------- Entry point ----------
if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception as e:
        messagebox.showerror("Fatal Error", str(e))
