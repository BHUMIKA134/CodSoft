#!/usr/bin/env python3
"""
Contact Management System — Internship Project
Features:
- SQLite database for permanent storage
- Add, View, Search, Update, Delete contacts
- Tkinter GUI with modern design
"""

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

# -----------------------------
# Database Setup
# -----------------------------
def init_db():
    conn = sqlite3.connect("contacts.db")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    address TEXT
                )''')
    conn.commit()
    conn.close()

# -----------------------------
# Main Application Class
# -----------------------------
class ContactApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📒 Contact Management System")
        self.root.geometry("750x500")
        self.root.config(bg="#f5f6fa")

        # Title
        title = tk.Label(root, text="Contact Management System",
                         font=("Helvetica", 20, "bold"), bg="#f5f6fa", fg="#2d3436")
        title.pack(pady=10)

        # Form Frame
        form_frame = tk.Frame(root, bg="#f5f6fa")
        form_frame.pack(pady=5)

        tk.Label(form_frame, text="Name:", font=("Helvetica", 12), bg="#f5f6fa").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text="Phone:", font=("Helvetica", 12), bg="#f5f6fa").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text="Email:", font=("Helvetica", 12), bg="#f5f6fa").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        tk.Label(form_frame, text="Address:", font=("Helvetica", 12), bg="#f5f6fa").grid(row=3, column=0, sticky="w", padx=10, pady=5)

        self.name_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.address_var = tk.StringVar()

        tk.Entry(form_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, padx=10, pady=5)
        tk.Entry(form_frame, textvariable=self.phone_var, width=40).grid(row=1, column=1, padx=10, pady=5)
        tk.Entry(form_frame, textvariable=self.email_var, width=40).grid(row=2, column=1, padx=10, pady=5)
        tk.Entry(form_frame, textvariable=self.address_var, width=40).grid(row=3, column=1, padx=10, pady=5)

        # Buttons
        btn_frame = tk.Frame(root, bg="#f5f6fa")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add Contact", width=15, command=self.add_contact, bg="#00b894", fg="white").grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update Contact", width=15, command=self.update_contact, bg="#0984e3", fg="white").grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Delete Contact", width=15, command=self.delete_contact, bg="#d63031", fg="white").grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Clear Fields", width=15, command=self.clear_fields, bg="#636e72", fg="white").grid(row=0, column=3, padx=5)

        # Search
        search_frame = tk.Frame(root, bg="#f5f6fa")
        search_frame.pack(pady=5)

        tk.Label(search_frame, text="Search by Name/Phone:", font=("Helvetica", 12), bg="#f5f6fa").grid(row=0, column=0, padx=10)
        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var, width=30).grid(row=0, column=1, padx=10)
        tk.Button(search_frame, text="Search", command=self.search_contact, bg="#6c5ce7", fg="white").grid(row=0, column=2, padx=5)
        tk.Button(search_frame, text="Show All", command=self.load_contacts, bg="#2d3436", fg="white").grid(row=0, column=3, padx=5)

        # Contact List
        self.tree = ttk.Treeview(root, columns=("id", "name", "phone", "email", "address"), show="headings", height=10)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("email", text="Email")
        self.tree.heading("address", text="Address")

        self.tree.column("id", width=30)
        self.tree.column("name", width=150)
        self.tree.column("phone", width=120)
        self.tree.column("email", width=180)
        self.tree.column("address", width=200)

        self.tree.pack(pady=10, fill="x", padx=10)
        self.tree.bind("<ButtonRelease-1>", self.fill_fields_from_selection)

        # Load initial contacts
        self.load_contacts()

    # -----------------------------
    # Functions
    # -----------------------------
    def run_query(self, query, params=()):
        conn = sqlite3.connect("contacts.db")
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        conn.close()

    def fetch_query(self, query, params=()):
        conn = sqlite3.connect("contacts.db")
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return rows

    def add_contact(self):
        name, phone, email, address = self.name_var.get(), self.phone_var.get(), self.email_var.get(), self.address_var.get()
        if name == "" or phone == "":
            messagebox.showwarning("Input Error", "Name and Phone are required!")
            return
        self.run_query("INSERT INTO contacts (name, phone, email, address) VALUES (?, ?, ?, ?)",
                       (name, phone, email, address))
        messagebox.showinfo("Success", "Contact added successfully!")
        self.load_contacts()
        self.clear_fields()

    def load_contacts(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.fetch_query("SELECT * FROM contacts")
        for row in rows:
            self.tree.insert("", "end", values=row)

    def search_contact(self):
        keyword = self.search_var.get()
        if keyword == "":
            messagebox.showwarning("Input Error", "Enter a name or phone to search!")
            return
        rows = self.fetch_query("SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ?", 
                                ('%' + keyword + '%', '%' + keyword + '%'))
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in rows:
            self.tree.insert("", "end", values=row)

    def fill_fields_from_selection(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, "values")
        self.name_var.set(values[1])
        self.phone_var.set(values[2])
        self.email_var.set(values[3])
        self.address_var.set(values[4])

    def update_contact(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Select a contact to update!")
            return
        values = self.tree.item(selected, "values")
        contact_id = values[0]

        name, phone, email, address = self.name_var.get(), self.phone_var.get(), self.email_var.get(), self.address_var.get()
        self.run_query("UPDATE contacts SET name=?, phone=?, email=?, address=? WHERE id=?",
                       (name, phone, email, address, contact_id))
        messagebox.showinfo("Success", "Contact updated successfully!")
        self.load_contacts()
        self.clear_fields()

    def delete_contact(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Selection Error", "Select a contact to delete!")
            return
        values = self.tree.item(selected, "values")
        contact_id = values[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {values[1]}?")
        if confirm:
            self.run_query("DELETE FROM contacts WHERE id=?", (contact_id,))
            messagebox.showinfo("Deleted", "Contact deleted successfully!")
            self.load_contacts()
            self.clear_fields()

    def clear_fields(self):
        self.name_var.set("")
        self.phone_var.set("")
        self.email_var.set("")
        self.address_var.set("")

# -----------------------------
# Run the App
# -----------------------------
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = ContactApp(root)
    root.mainloop()
