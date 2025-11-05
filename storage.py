# storage.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from models import Session, Task, engine, Base

# Ensure tables exist (safe to call multiple times)
Base.metadata.create_all(engine)

def _row_to_dict(row: Task) -> Dict[str, Any]:
    """Convert a Task row to a plain dict (same shape logic.py expects)."""
    return {
        "id": row.id,
        "title": row.title,
        "category": row.category,
        "due_datetime": row.due_datetime,
        "locked": bool(row.locked),
        "fixed_pos": row.fixed_pos,
        "part_label": row.part_label,
        "is_done": bool(row.is_done),
        "is_gym": bool(row.is_gym),
        "in_main": bool(getattr(row, "in_main", False)),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }

def add_task(title: str, category: str, due_datetime: datetime,
             part_label: Optional[str] = None, is_gym: bool = False, in_main: bool = False) -> int:
    """Create a task and return its new id."""
    s = Session()
    t = Task(
        title=title,
        category=category,
        due_datetime=due_datetime,
        part_label=part_label,
        is_gym=is_gym,
        in_main=in_main,
        locked=False,
        is_done=False
    )
    s.add(t)
    s.commit()
    new_id = t.id
    s.close()
    return new_id

def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Return a task dict or None if not found."""
    s = Session()
    row = s.get(Task, task_id)
    s.close()
    if row:
        return _row_to_dict(row)
    return None

def get_all_tasks(include_done: bool = False) -> List[Dict[str, Any]]:
    """
    Return all tasks as dicts.
    By default excludes tasks where is_done==True (completed).
    """
    s = Session()
    stmt = select(Task)
    rows = s.execute(stmt).scalars().all()
    s.close()
    result = []
    for r in rows:
        if not include_done and r.is_done:
            continue
        result.append(_row_to_dict(r))
    return result

def update_task(task_id: int, **fields) -> bool:
    """
    Update fields on a task. fields example: title="New", due_datetime=dt, category="Home"
    Returns True if updated, False if not found.
    """
    s = Session()
    row = s.get(Task, task_id)
    if not row:
        s.close()
        return False
    # Only update accepted attributes to avoid mistakes
    allowed = {"title", "category", "due_datetime", "part_label", "is_gym", "fixed_pos", "locked", "is_done", "in_main"}
    for k, v in fields.items():
        if k in allowed:
            setattr(row, k, v)
    s.commit()
    s.close()
    return True

def set_locked(task_id: int, locked: bool, fixed_pos: Optional[int] = None) -> bool:
    """
    Mark a task locked/unlocked. If locking, you can pass fixed_pos (int).
    If unlocking, fixed_pos will be cleared unless you pass a specific value.
    """
    s = Session()
    row = s.get(Task, task_id)
    if not row:
        s.close()
        return False
    row.locked = bool(locked)
    # Only set fixed_pos if provided and an int; clear if unlocking and not provided
    if isinstance(fixed_pos, int):
        row.fixed_pos = fixed_pos
    elif not locked:
        row.fixed_pos = None
    s.commit()
    s.close()
    return True

def mark_done(task_id: int) -> bool:
    """Mark a task as done (is_done=True)."""
    return update_task(task_id, is_done=True)

def delete_task(task_id: int) -> bool:
    """Delete a task row; returns True if deleted."""
    s = Session()
    row = s.get(Task, task_id)
    if not row:
        s.close()
        return False
    s.delete(row)
    s.commit()
    s.close()
    return True

def remove_expired(now: Optional[datetime] = None) -> List[int]:
    """
    Remove tasks whose due_datetime <= now AND not done.
    Returns list of removed task ids for notifying the UI.
    """
    if now is None:
        now = datetime.now()
    s = Session()
    stmt = select(Task).where(Task.due_datetime <= now, Task.is_done == False)
    rows = s.execute(stmt).scalars().all()
    removed_ids = [r.id for r in rows]
    for r in rows:
        s.delete(r)
    s.commit()
    s.close()
    return removed_ids