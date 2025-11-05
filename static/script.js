// static/script.js

// ---- small helpers ----
function htmlToElement(html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstChild;
}
function escapeHtml(unsafe) {
  if (!unsafe) return '';
  return String(unsafe).replace(/[&<"'>]/g, function (m) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m];
  });
}

// show a bootstrap toast in #toast-area
function showToast(message, ttl = 5000) {
  try {
    const id = 'toast-' + Date.now();
    const html = `
      <div id="${id}" class="toast align-items-center text-white bg-dark border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
          <div class="toast-body">${escapeHtml(message)}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
      </div>
    `;
    const area = document.getElementById('toast-area');
    if (!area) return console.warn('No toast area found');
    area.insertAdjacentHTML('beforeend', html);
    const el = document.getElementById(id);
    const bsToast = bootstrap.Toast.getOrCreateInstance(el, { delay: ttl });
    bsToast.show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
  } catch (e) {
    console.error('showToast failed', e);
  }
}

// ---- rendering ----
function renderTaskItem(t) {
  const dueIso = t.due_datetime || t.due || '';
  const dueDate = dueIso ? new Date(dueIso) : null;
  const dueStr = dueDate && !isNaN(dueDate.getTime())
    ? dueDate.toLocaleString([], { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
    : (dueIso || '');
  const partLabel = t.part_label ? `<small class="text-muted ms-2">[${escapeHtml(t.part_label)}]</small>` : '';
  const lockSymbol = t.locked ? '✔' : '◻';

  return `
    <li class="list-group-item d-flex justify-content-between align-items-center"
        data-task-id="${t.id}"
        data-due="${escapeHtml(dueIso)}"
        data-locked="${t.locked ? '1' : '0'}">
      <span class="drag-handle me-2" style="cursor:grab">⋮⋮</span>

      <div class="flex-grow-1">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong class="task-title">${escapeHtml(t.title)}</strong>
            ${partLabel}
            <small class="text-muted">(${escapeHtml(t.category || '')})</small>
          </div>

          <div>
            <button class="btn btn-sm lock-btn" data-locked="${t.locked ? '1' : '0'}" title="Lock/Unlock">
              <span class="lock-indicator">${lockSymbol}</span>
            </button>
          </div>
        </div>

        <div class="mt-1">
          <small class="text-muted edit-due" style="cursor:pointer" title="Edit due date/time">Due: ${escapeHtml(dueStr)}</small>
          <button class="btn btn-sm btn-outline-secondary ms-2 split-btn" title="Split task">Split</button>
        </div>
      </div>

      <div class="ms-3">
        <a href="/done/${t.id}" class="btn btn-sm btn-outline-success">✓</a>
        <a href="/delete/${t.id}" class="btn btn-sm btn-outline-danger">🗑️</a>
      </div>
    </li>
  `;
}

function renderLists(data) {
  const mainBlock = document.getElementById('main-block');
  const awBlock = document.getElementById('awaragardi-block');
  const homeBlock = document.getElementById('home-block');

  function populate(ul, items) {
    ul.innerHTML = '';
    if (!items || items.length === 0) {
      ul.innerHTML = '<li class="list-group-item text-muted text-center">No tasks yet</li>';
      return;
    }
    for (const t of items) {
      ul.appendChild(htmlToElement(renderTaskItem(t)));
    }
  }

  populate(mainBlock, data.main_list);
  populate(awBlock, data.awaragardi_list);
  populate(homeBlock, data.home_list);

  // Attach row handlers after rendering
  attachRowHandlers();
}

// ---- sortable + drag logic ----
let isDragging = false;
function initSortable() {
  const mainEl = document.getElementById('main-block');
  const awEl = document.getElementById('awaragardi-block');
  const homeEl = document.getElementById('home-block');

  const groups = { name: 'shared', pull: true, put: true };

  async function onEndHandler(evt) {
    isDragging = false;
    const itemEl = evt.item;
    const taskId = itemEl.getAttribute('data-task-id');
    const fromList = evt.from ? evt.from.id : null;
    const toList = evt.to ? evt.to.id : null;
    const newIndex = evt.newIndex;

    // Rules:
    // - side -> main allowed
    // - side -> side not allowed
    // - main -> side not allowed (revert)
    // - main -> main = reorder inside main -> lock the task
    try {
      // side -> side (reject)
      if (fromList !== 'main-block' && toList !== 'main-block') {
        showToast('Cannot move directly between side banks.');
        await fetchAndRender();
        return;
      }

      // main -> side (reject)
      if (fromList === 'main-block' && toList !== 'main-block') {
        showToast('Cannot move tasks out of Main back to side banks.');
        await fetchAndRender();
        return;
      }

      // side -> main (allowed): do NOT lock, mark as in_main on server
      if (fromList !== 'main-block' && toList === 'main-block') {
        const resp = await fetch('/move', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_id: taskId,
            new_index: newIndex,
            new_category: 'Main',
            locked: false
          })
        });
        const j = await resp.json();
        if (j && j.main_list) {
          renderLists(j);
          if (j.removed_expired && j.removed_expired.length) showToast(`${j.removed_expired.length} task(s) expired and removed.`);
        } else {
          await fetchAndRender();
        }
        return;
      }

      // main -> main (reorder inside main) : lock the task at newIndex
      if (fromList === 'main-block' && toList === 'main-block') {
        const resp = await fetch('/move', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            task_id: taskId,
            new_index: newIndex,
            new_category: 'Main',
            locked: true
          })
        });
        const j = await resp.json();
        if (j && j.main_list) {
          renderLists(j);
          if (j.removed_expired && j.removed_expired.length) showToast(`${j.removed_expired.length} task(s) expired and removed.`);
        } else {
          await fetchAndRender();
        }
        return;
      }

      // fallback - refresh canonical state
      await fetchAndRender();
    } catch (err) {
      console.error('Move failed', err);
      showToast('Move failed (see console).');
      await fetchAndRender();
    }
  }

  new Sortable(mainEl, { group: groups, animation: 150, handle: '.drag-handle', onStart: () => { isDragging = true; }, onEnd: onEndHandler });
  new Sortable(awEl, { group: groups, animation: 150, handle: '.drag-handle', onStart: () => { isDragging = true; }, onEnd: onEndHandler });
  new Sortable(homeEl, { group: groups, animation: 150, handle: '.drag-handle', onStart: () => { isDragging = true; }, onEnd: onEndHandler });
}

// ---- fetch and render ----
async function fetchAndRender() {
  if (isDragging) return;
  try {
    const resp = await fetch('/api/tasks');
    const data = await resp.json();
    renderLists(data);
    if (data.removed_expired && data.removed_expired.length) {
      showToast(`${data.removed_expired.length} task(s) expired and were removed.`);
    }
  } catch (err) {
    console.error('Failed to fetch tasks', err);
  }
}

// ---- row event handlers (lock, split, edit-due) ----
function attachRowHandlers() {
  // LOCK button behavior (explicit toggle)
  document.querySelectorAll('.lock-btn').forEach(btn => {
    btn.onclick = async (e) => {
      e.preventDefault();
      const li = btn.closest('li[data-task-id]');
      const taskId = li.getAttribute('data-task-id');
      const currentlyLocked = btn.getAttribute('data-locked') === '1';
      if (currentlyLocked) {
        if (!confirm('Make this task eligible for automatic reordering again?')) return;
        // explicit unlock: update locked=false, clear fixed_pos
        try {
          const resp = await fetch(`/update/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ locked: false, fixed_pos: null })
          });
          const j = await resp.json();
          if (j && j.main_list) renderLists(j); else fetchAndRender();
          showToast('Task unlocked (auto-reorder enabled).');
        } catch (err) {
          console.error('Unlock failed', err);
          showToast('Failed to unlock task.');
        }
      } else {
        // explicit lock: find index if in main, otherwise lock at 0 by default
        const parentUl = li.closest('ul');
        let idx = 0;
        if (parentUl && parentUl.id === 'main-block') {
          idx = Array.from(parentUl.children).indexOf(li);
        }
        try {
          const resp = await fetch('/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId, new_index: idx, new_category: 'Main', locked: true })
          });
          const j = await resp.json();
          if (j && j.main_list) renderLists(j); else fetchAndRender();
          showToast('Task locked in Main.');
        } catch (err) {
          console.error('Lock failed', err);
          showToast('Failed to lock task.');
        }
      }
    };
  });

  // SPLIT button behavior
  document.querySelectorAll('.split-btn').forEach(btn => {
    btn.onclick = async (e) => {
      e.preventDefault();
      const li = btn.closest('li[data-task-id]');
      const taskId = li.getAttribute('data-task-id');
      if (!confirm('Split this task into parts?')) return;
      try {
        const resp = await fetch(`/split/${taskId}`, { method: 'POST' });
        if (resp.status === 404) {
          showToast('Split endpoint not available on server.');
          return;
        }
        const j = await resp.json();
        if (j && j.main_list) {
          renderLists(j);
          showToast('Task split.');
        } else {
          fetchAndRender();
          showToast('Task split (server response).');
        }
      } catch (err) {
        console.error('Split failed', err);
        showToast('Split failed (see console).');
      }
    };
  });

  // EDIT DUE behavior (opens modal, saves)
  document.querySelectorAll('.edit-due').forEach(el => {
    el.onclick = (e) => {
      const li = el.closest('li[data-task-id]');
      const taskId = li.getAttribute('data-task-id');
      const dueIso = li.getAttribute('data-due') || '';
      const dateInput = document.getElementById('edit-due-date');
      const timeInput = document.getElementById('edit-due-time');
      const hiddenId = document.getElementById('edit-task-id');
      hiddenId.value = taskId;
      if (dueIso) {
        const d = new Date(dueIso);
        if (!isNaN(d.getTime())) {
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, '0');
          const dd = String(d.getDate()).padStart(2, '0');
          const hh = String(d.getHours()).padStart(2, '0');
          const mins = String(d.getMinutes()).padStart(2, '0');
          dateInput.value = `${yyyy}-${mm}-${dd}`;
          timeInput.value = `${hh}:${mins}`;
        } else {
          dateInput.value = '';
          timeInput.value = '';
        }
      } else {
        dateInput.value = '';
        timeInput.value = '';
      }
      const modalEl = document.getElementById('editDueModal');
      const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
      bsModal.show();
    };
  });

// Save button on modal
const saveBtn = document.getElementById('edit-due-save');
if (saveBtn) {
  saveBtn.onclick = async () => {
    const hiddenId = document.getElementById('edit-task-id').value;
    const dateInput = document.getElementById('edit-due-date').value; // "YYYY-MM-DD"
    const timeInput = document.getElementById('edit-due-time').value; // "HH:MM"
    if (!dateInput || !timeInput) {
      showToast('Please enter both date and time.');
      return;
    }

    // Build a local (naive) ISO-like string WITHOUT timezone conversion.
    // Example: "2025-11-06T14:30"
    const localIso = `${dateInput}T${timeInput}`;

    try {
      const resp = await fetch(`/update/${hiddenId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ due_datetime: localIso })
      });
      if (resp.status === 404) {
        showToast('Update endpoint not available on server.');
      } else {
        const j = await resp.json();
        if (j && j.main_list) renderLists(j); else fetchAndRender();
        showToast('Due date updated.');
      }
    } catch (err) {
      console.error('Update failed', err);
      showToast('Failed to update due date.');
    } finally {
      const modalEl = document.getElementById('editDueModal');
      const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
      bsModal.hide();
    }
  };
}}

// ---- boot ----
window.addEventListener('DOMContentLoaded', () => {
  initSortable();
  fetchAndRender();
  setInterval(fetchAndRender, 10000);
});
