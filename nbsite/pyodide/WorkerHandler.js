const pyodideWorker = new Worker(DOCUMENTATION_OPTIONS.URL_ROOT + '_static/PyodideWebWorker.js');

pyodideWorker.documents = {}

function send_change(jsdoc, doc_id, event) {
  if (event.setter_id != null)
    return
  const patch = jsdoc.create_json_patch_string([event])
  pyodideWorker.postMessage({type: 'patch', patch: patch, id: doc_id})
}

function loadScripts(scripts) {
  console.log(scripts)
  return scripts.reduce(function(cur, next){ 
    return cur.then($.getScript.bind($, next));
  }, $.when());
}

pyodideWorker.onmessage = async (event) => {
  const button = document.getElementById(`button-${event.data.id}`)
  const output = document.getElementById(`output-${event.data.id}`)
  const stdout = document.getElementById(`stdout-${event.data.id}`)
  const stderr = document.getElementById(`stderr-${event.data.id}`)
  const msg = event.data;
  if (msg.type === 'loading') {
    _ChangeTooltip(button, msg.msg)
    _ChangeIcon(button, iconLoading)
  } else if (msg.type === 'loaded') {
    _ChangeTooltip(button, 'Executing code')
  } else if (msg.type === 'error') {
    _ChangeTooltip(button, msg.msg)
    _ChangeIcon(button, iconError)
  } else if (msg.type === 'idle') {
    _ChangeTooltip(button, 'Executed successfully')
    _ChangeIcon(button, iconLoaded)
  } else if (msg.type === 'stdout') {
    const stdout = document.getElementById(`stdout-${msg.id}`)
    stdout.style.display = 'block';
    stdout.innerText += msg.content
  } else if (msg.type === 'stderr') {
    const stderr = document.getElementById(`stderr-${msg.id}`)
    stderr.style.display = 'block';
    stderr.innerText += msg.content
  } else if (msg.type === 'render') {
    output.style.display = 'block';
    output.setAttribute('class', 'pyodide-output live')
    if (msg.mime === 'application/bokeh') {
      const [view] = await Bokeh.embed.embed_item(JSON.parse(msg.content))

      // Setup bi-directional syncing
      pyodideWorker.documents[msg.id] = jsdoc = view.model.document
      jsdoc.on_change(send_change.bind(null, jsdoc, msg.id), false)
    } else if (msg.mime === 'text/plain') {
      output.innerHTML = `<pre>${msg.content}</pre>`;
    } else if (msg.mime === 'text/html') {
      output.innerHTML = `<div class="pyodide-output-wrapper">${msg.content}</div>`
    }
    pyodideWorker.postMessage({type: 'rendered', id: msg.id, mime: msg.mime})
  } else if (msg.type === 'patch') {
    pyodideWorker.documents[msg.id].apply_json_patch(JSON.parse(msg.patch), msg.buffers, setter_id='js')
  }
};

window.pyodideWorker = pyodideWorker;
