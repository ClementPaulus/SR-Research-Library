/* Autosave the guided editor every 20 s of inactivity, with optimistic version tokens.
   A 409 means another tab saved first: we show the conflict and stop, never overwrite. */
(function () {
  var form = document.getElementById('draft-form');
  if (!form || !window.fetch) return;
  var url = form.dataset.autosave;
  var versionInput = form.querySelector('input[name=draft_version]');
  var status = document.getElementById('autosave-status');
  var timer = null, dirty = false, conflicted = false;
  function say(text) { if (status) status.textContent = text; }
  function collect() {
    var data = {};
    var elements = form.elements;
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (!el.name || el.name === 'csrfmiddlewaretoken' || el.name === 'draft_version' || el.name === 'action') continue;
      if (el.multiple) { data[el.name] = Array.prototype.filter.call(el.options, function (o) { return o.selected; }).map(function (o) { return o.value; }); }
      else if (el.type === 'checkbox') { data[el.name] = el.checked; }
      else { data[el.name] = el.value; }
    }
    return data;
  }
  function schedule() { if (conflicted) return; dirty = true; clearTimeout(timer); timer = setTimeout(save, 20000); say('Unsaved changes…'); }
  async function save() {
    if (!dirty || conflicted) return;
    var payload = { form: collect(), draft_version: parseInt(versionInput.value, 10) };
    say('Saving…');
    var response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('input[name=csrfmiddlewaretoken]').value }, body: JSON.stringify(payload) });
    if (response.status === 409) {
      conflicted = true;
      var body = await response.json();
      say('Another tab saved a newer version (v' + body.draft_version + '). Reload to review before continuing; your unsaved edits here were not applied.');
      return;
    }
    if (!response.ok) { say('Autosave could not save this draft yet; use Save draft.'); return; }
    var result = await response.json();
    versionInput.value = result.draft_version;
    dirty = false;
    say('Saved (v' + result.draft_version + ')');
  }
  form.addEventListener('input', schedule);
  form.addEventListener('change', schedule);
})();
