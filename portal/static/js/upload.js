/* Upload progress with client-side SHA-256 (advisory only; the server verifies bytes independently).
   Works without this script: the plain form POST still uploads. */
(function () {
  var form = document.querySelector('form[data-upload]');
  if (!form || !window.fetch || !window.crypto || !window.crypto.subtle) return;
  var input = form.querySelector('input[type=file]');
  var bar = document.getElementById('upload-progress');
  var status = document.getElementById('upload-status');
  var list = document.getElementById('upload-list');

  function hex(buffer) {
    return Array.prototype.map.call(new Uint8Array(buffer), function (b) { return ('00' + b.toString(16)).slice(-2); }).join('');
  }
  async function sha256(file) {
    if (file.size > 64 * 1024 * 1024) return '';
    var buf = await file.arrayBuffer();
    return hex(await crypto.subtle.digest('SHA-256', buf));
  }
  function say(text) { if (status) status.textContent = text; }

  form.addEventListener('submit', async function (event) {
    if (!input || !input.files.length) return;
    if (form.dataset.upload !== 'ajax') return;
    event.preventDefault();
    var token = form.querySelector('input[name=csrfmiddlewaretoken]').value;
    var total = input.files.length, done = 0;
    for (var i = 0; i < total; i++) {
      var file = input.files[i];
      say('Saving ' + file.name + ' (' + (i + 1) + ' of ' + total + ')…');
      var data = new FormData();
      data.append('files', file, file.name);
      data.append('client_sha256', await sha256(file));
      var ok = await new Promise(function (resolve) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', form.action);
        xhr.setRequestHeader('X-CSRFToken', token);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.upload.onprogress = function (e) { if (bar && e.lengthComputable) { bar.max = e.total; bar.value = e.loaded; } };
        xhr.onload = function () {
          var payload = {};
          try { payload = JSON.parse(xhr.responseText); } catch (err) {}
          if (xhr.status >= 200 && xhr.status < 300) {
            if (list) { var li = document.createElement('li'); li.textContent = file.name + ' — saved'; list.appendChild(li); }
            resolve(true);
          } else {
            say((payload.message || 'Upload failed') + ' — nothing was duplicated; you can retry.');
            resolve(false);
          }
        };
        xhr.onerror = function () { say('Connection interrupted while saving ' + file.name + '. Retry: a completed file is never duplicated.'); resolve(false); };
        xhr.send(data);
      });
      if (!ok) return;
      done++;
    }
    say('Your files are saved. We’re preparing a draft for your review.');
    window.location.reload();
  });
})();
