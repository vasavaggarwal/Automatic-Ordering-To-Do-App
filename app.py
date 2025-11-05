# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import logic, storage

app = Flask(__name__)


def _to_iso(val):
    if val is None:
        return None
    try:
        from datetime import datetime as _dt
        if isinstance(val, _dt):
            return val.isoformat()
    except Exception:
        pass
    try:
        return str(val)
    except Exception:
        return None


def _canonical_lists_and_response():
    """Return canonical lists: main = in_main OR necessary/college; side lists exclude in_main; include removed_expired."""
    now = datetime.now()
    removed_expired = storage.remove_expired(now)
    all_tasks = storage.get_all_tasks()

    # Main workspace contains tasks that are explicitly in_main OR tasks that are by-design in main (Necessary/College)
    tasks_for_main = [t for t in all_tasks if t.get("in_main") or t.get("category") in ("Necessary", "College")]
    main_list = logic.compile_main(tasks_for_main, now)

    # Side banks must exclude tasks that are currently placed in_main
    awaragardi_list = [t for t in all_tasks if t.get("category") == "Awaragardi" and not t.get("is_done") and not t.get("in_main")]
    home_list = [t for t in all_tasks if t.get("category") == "Home" and not t.get("is_done") and not t.get("in_main")]

    def _serial(task):
        return {
            **task,
            "due_datetime": _to_iso(task.get("due_datetime")),
            "created_at": _to_iso(task.get("created_at")),
            "updated_at": _to_iso(task.get("updated_at")),
        }

    return {
        "main_list": [_serial(t) for t in main_list],
        "awaragardi_list": [_serial(t) for t in awaragardi_list],
        "home_list": [_serial(t) for t in home_list],
        "removed_expired": removed_expired
    }


@app.route('/')
def index():
    now = datetime.now()
    storage.remove_expired(now)
    all_tasks = storage.get_all_tasks()
    tasks_for_main = [t for t in all_tasks if t.get("in_main") or t.get("category") in ("Necessary", "College")]
    main_list = logic.compile_main(tasks_for_main, now)
    awaragardi_list = [t for t in all_tasks if t.get("category") == "Awaragardi" and not t.get("is_done") and not t.get("in_main")]
    home_list = [t for t in all_tasks if t.get("category") == "Home" and not t.get("is_done") and not t.get("in_main")]
    return render_template('index.html', main_list=main_list, awaragardi_list=awaragardi_list, home_list=home_list)


@app.route('/api/tasks')
def api_tasks():
    return jsonify(_canonical_lists_and_response())


@app.route('/add', methods=['POST'])
def add_task():
    title = request.form.get('title')
    category = request.form.get('category')
    date_str = request.form.get('due_date')
    time_str = request.form.get('due_time')
    if not (title and category and date_str and time_str):
        return redirect(url_for('index'))
    try:
        due_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except Exception:
        return redirect(url_for('index'))
    # default in_main False for newly created tasks (they live in their category bank)
    storage.add_task(title, category, due_datetime, in_main=False)
    return redirect(url_for('index'))


@app.route('/done/<int:task_id>')
def mark_done(task_id):
    storage.mark_done(task_id)
    return redirect(url_for('index'))


@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    storage.delete_task(task_id)
    return redirect(url_for('index'))


@app.route('/move', methods=['POST'])
def move_task():
    """
    Server-side enforcement of drag/drop rules:

    - Side -> Main:
        * allowed. Set in_main=True, locked=False (eligible for reordering).
        * category remains unchanged.
    - Side -> Side:
        * rejected (400).
    - Main -> Side:
        * rejected (400).
    - Main -> Main (reorder inside Main):
        * allowed. If client indicates locked=True (reorder-as-lock), server sets locked=True and fixed_pos=new_index.
          Otherwise, if client passes locked=False, server keeps locked=False (no change) but will re-run compile_main to
          place items (client should pass locked=true when they want to lock at position).
    Response: canonical lists JSON.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "reason": "bad json"}), 400

    task_id = data.get('task_id')
    new_index = data.get('new_index')
    new_category = data.get('new_category')  # "Main", "Home", "Awaragardi", or None
    client_locked = bool(data.get('locked', False))

    try:
        task_id = int(task_id)
    except Exception:
        return jsonify({"status": "error", "reason": "invalid task_id"}), 400

    # coerce new_index
    idx = None
    if new_index is not None:
        try:
            idx = int(new_index)
            if idx < 0:
                idx = None
        except Exception:
            idx = None

    current = storage.get_task(task_id)
    if not current:
        return jsonify({"status": "error", "reason": "task not found"}), 404

    src_in_main = bool(current.get("in_main"))
    src_cat = current.get("category")

    # Side -> Side (both not in main): reject
    if not src_in_main and new_category and new_category != "Main":
        # moving from a side bank to another side bank
        return jsonify({"status": "error", "reason": "cannot move directly between side banks"}), 400

    # Main -> Side: reject (once in main, cannot go back)
    if src_in_main and new_category and new_category != "Main":
        return jsonify({"status": "error", "reason": "cannot move tasks out of Main back to side banks"}), 400

    # Moving into Main
    if new_category == "Main":
        if not src_in_main:
            # side -> main: mark in_main true, ensure unlocked
            storage.update_task(task_id, in_main=True)
            storage.set_locked(task_id, False, fixed_pos=None)
        else:
            # already in main and reordering within main
            # If client requests lock (client_locked==True), set locked True at position idx
            if client_locked:
                storage.set_locked(task_id, True, fixed_pos=idx)
            else:
                # client didn't ask to lock - ensure it's not locked
                storage.set_locked(task_id, False, fixed_pos=None)
    else:
        # new_category is None or a side - handled above, but ensure safe default
        pass

    return jsonify(_canonical_lists_and_response())


@app.route('/update/<int:task_id>', methods=['POST'])
def update_task(task_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "reason": "bad json"}), 400

    fields = {}
    if 'due_datetime' in data and data['due_datetime']:
        raw = data['due_datetime']
        parsed = None
        # Try Python 3.7+ fromisoformat (accepts 'YYYY-MM-DDTHH:MM:SS' and 'YYYY-MM-DDTHH:MM')
        try:
            parsed = datetime.fromisoformat(raw)
        except Exception:
            # Fallbacks: 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DDTHH:MM'
            from datetime import datetime as _dt
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
                try:
                    parsed = _dt.strptime(raw, fmt)
                    break
                except Exception:
                    parsed = None
        if not parsed:
            return jsonify({"status": "error", "reason": "invalid due_datetime"}), 400
        fields['due_datetime'] = parsed


    # allow title/category/part_label/is_gym/is_done/in_main/fixed_pos/locked
    for k in ("title", "category", "part_label", "is_gym", "is_done", "fixed_pos", "locked", "in_main"):
        if k in data:
            fields[k] = data[k]

    updated = storage.update_task(task_id, **fields)
    if not updated:
        return jsonify({"status": "error", "reason": "not found"}), 404

    return jsonify(_canonical_lists_and_response())


@app.route('/split/<int:task_id>', methods=['POST'])
def split_task(task_id):
    orig = storage.get_task(task_id)
    if not orig:
        return jsonify({"status": "error", "reason": "not found"}), 404

    new_title = orig["title"]
    new_category = orig["category"]
    new_due = orig["due_datetime"]
    new_part = None

    if orig.get("part_label"):
        try:
            base, num = orig["part_label"].rsplit(" ", 1)
            num = int(num)
            new_part = f"{base} {num + 1}"
        except Exception:
            new_part = orig["part_label"] + " (copy)"
    else:
        storage.update_task(task_id, part_label="Part 1")
        new_part = "Part 2"

    # duplicate inherits in_main state (so copy appears where expected)
    storage.add_task(new_title, new_category, new_due, part_label=new_part, is_gym=orig.get("is_gym", False), in_main=bool(orig.get("in_main")))

    return jsonify(_canonical_lists_and_response())


if __name__ == '__main__':
    app.run(debug=True)