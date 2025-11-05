# logic.py
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Category base ranks (lower = higher priority)
CATEGORY_RANK = {
    "Necessary": 1,
    "College": 2,
    "Home": 3,
    "Awaragardi": 4
}

def _priority_key(task: Dict[str, Any], now: datetime) -> tuple:
    """
    Compute a sort key for reorderable tasks.
    Rules:
      1. Primary: earlier due_datetime sorts first.
      2. If due_datetime is same, category priority applies:
         Necessary < College < Home < Awaragardi.
      3. College tasks due in <24h get topmost priority (effective rank 0).
      4. Earlier created tasks break ties.
    """
    due = task["due_datetime"]
    hours_left = (due - now).total_seconds() / 3600.0

    # College boost
    if task.get("category") == "College" and hours_left < 24:
        category_rank = 0
    else:
        category_rank = CATEGORY_RANK.get(task.get("category"), 99)

    # Sort primarily by due time, then category rank, then creation time
    created_at = task.get("created_at") or datetime.min
    return (due, category_rank, created_at)


def sort_reorderable(tasks: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    """
    Return reorderable (unlocked, active) tasks sorted according to plan rules.
    """
    valid = []
    for t in tasks:
        if t.get("is_done"):
            continue
        if t.get("locked"):
            continue
        if t.get("due_datetime") <= now:
            continue
        valid.append(t)

    # Sort by primary due time, then category, then created_at
    return sorted(valid, key=lambda t: _priority_key(t, now))

def compile_main(all_tasks: List[Dict[str, Any]], now: datetime = None) -> List[Dict[str, Any]]:
    """
    Build the ordered 'Main' list (mix of fixed + reorderable) from all task dicts.
    Rules:
      - Fixed tasks (locked==True) must appear at/near their fixed_pos.
      - Reorderable tasks fill the empty slots in order produced by sort_reorderable().
      - If fixed positions collide, later fixed tasks are shifted to the next free slot.
      - The resulting list contains only tasks that are not done and not expired (due > now).
    Returns: ordered list of task dicts for rendering in Main.
    """
    if now is None:
        now = datetime.now()

    # Separate task buckets
    fixed_tasks = [t for t in all_tasks if t.get("locked") and not t.get("is_done")]
    # Only consider fixed tasks with a valid fixed_pos; if missing, treat as reorderable
    fixed_tasks = [t for t in fixed_tasks if isinstance(t.get("fixed_pos"), int) and t.get("due_datetime") > now]

    reorderable = sort_reorderable(all_tasks, now)

    # Determine size: at least enough to hold fixed positions and all items
    max_fixed_pos = max([t["fixed_pos"] for t in fixed_tasks], default=-1)
    needed_slots = max(max_fixed_pos + 1, len(fixed_tasks) + len(reorderable))

    # Create empty slots
    main_slots: List[Dict[str, Any] | None] = [None] * needed_slots

    # Place fixed tasks at their fixed_pos (resolve collisions by shifting forward)
    for ft in sorted(fixed_tasks, key=lambda x: x["fixed_pos"]):
        pos = ft["fixed_pos"]
        if pos < 0:
            pos = 0
        while pos < len(main_slots) and main_slots[pos] is not None:
            pos += 1
        if pos >= len(main_slots):
            main_slots.append(None)
        main_slots[pos] = ft

    # Fill empty slots with reorderable tasks left-to-right
    idx = 0
    for r in reorderable:
        # skip tasks that are already in fixed (defensive)
        if any(r.get("id") == ft.get("id") for ft in fixed_tasks):
            continue
        while idx < len(main_slots) and main_slots[idx] is not None:
            idx += 1
        if idx >= len(main_slots):
            main_slots.append(None)
        main_slots[idx] = r
        idx += 1

    # Compact and return only non-None entries, and also ensure no expired/done slipped in
    final = [t for t in main_slots if t is not None and not t.get("is_done") and t.get("due_datetime") > now]
    return final

def expired_tasks(tasks: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
    """
    Return a list of tasks whose due_datetime <= now (expired).
    Use this so the caller can remove them and show notifications.
    """
    return [t for t in tasks if t.get("due_datetime") <= now and not t.get("is_done")]

# Demo runner
if __name__ == "__main__":
    now = datetime.now()
    demo = [
        {"id": 1, "title": "A", "category": "Necessary", "due_datetime": now + timedelta(hours=30), "locked": False, "created_at": now - timedelta(hours=1), "is_done": False},
        {"id": 2, "title": "B", "category": "College", "due_datetime": now + timedelta(hours=20), "locked": False, "created_at": now - timedelta(hours=2), "is_done": False},
        {"id": 3, "title": "C", "category": "Home", "due_datetime": now + timedelta(hours=10), "locked": True, "fixed_pos": 0, "created_at": now - timedelta(hours=3), "is_done": False},
    ]
    main = compile_main(demo, now=now)
    print("Compiled Main order:", [t["title"] for t in main])