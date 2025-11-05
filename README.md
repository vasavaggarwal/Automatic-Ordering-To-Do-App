# Automatic Ordering To-Do App

A dynamic, category-aware task manager that automatically reorders your priorities based on due time and context.  
The app intelligently balances urgency (due date/time) with task category importance — helping you focus on what truly matters.

---

## 🚀 Features

- **Automatic Reordering:**  
  Tasks in the Main block are reordered by due date, time, and category priority:
  - Earlier due dates rank higher.
  - If due dates are equal:  
    `Necessary > College > Home > Awaragardi`
  - College tasks due within 24 hours jump to the very top.

- **Category-based Blocks:**
  - **Main Block:** Workspace where reordering happens.  
    Tasks from any category can be moved here.
  - **Home / Awaragardi Blocks:** Side “banks” to store pending items until needed.  
    Tasks moved from these banks into Main are removed from their original block.

- **Drag-and-Drop Sorting:**  
  Reorder within Main to fix (lock) a task at its position.

- **Date-Time Editor:**  
  Inline due date editing with an intuitive modal.

- **Smart Expiry:**  
  Tasks automatically disappear after their due time passes.

- **Split Tasks:**  
  Divide a task into parts (`Part 1`, `Part 2`, etc.) for better tracking.

---

## ⚙️ Tech Stack

- **Backend:** Flask + SQLAlchemy + APScheduler  
- **Frontend:** Bootstrap 5 + SortableJS  
- **Database:** SQLite (`db/tasks.db`)

---

## 📁 Directory Structure

```
project/
│
├── app.py               # Flask routes and API
├── logic.py             # Auto-reorder logic
├── models.py            # SQLAlchemy model (Task)
├── storage.py           # Database CRUD operations
│
├── static/
│   ├── script.js        # Frontend drag/drop logic
│   ├── style.css        # Custom UI styling
│   └── libs/            # SortableJS library
│
└── templates/
    ├── index.html       # Main UI
    ├── base.html        # Common layout
    └── add_task.html    # Add Task form
```

---

## 🧩 Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/<your-repo>/smart-todo.git
   cd smart-todo
   ```

2. **Create virtual environment & install requirements**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**
   ```bash
   python models.py
   ```

4. **Run the app**
   ```bash
   python app.py
   ```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧮 Priority Rules Summary

| Factor | Description |
|--------|--------------|
| **Due Time** | Earlier due time → higher priority |
| **Category** | Necessary > College > Home > Awaragardi |
| **College Boost** | College tasks due <24h rank highest |
| **Locking** | Drag inside Main to fix task order |
| **Side Banks** | Tasks moved into Main are removed from side blocks |

---

## 🧑‍💻 Developer Notes

- All timestamps are stored and displayed as local time.
- Removing or marking tasks done updates instantly.
- For DB schema changes, delete `db/tasks.db` and re-run `models.py`.
