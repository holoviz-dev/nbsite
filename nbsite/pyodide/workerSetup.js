const pyodideWorker = new Worker(DOCUMENTATION_OPTIONS.URL_ROOT + '_static/webWorker.js');

pyodideWorker.documents = {}

function send_change(jsdoc, doc_id, event) {
  if (event.setter_id != null)
    return
  const patch = jsdoc.create_json_patch_string([event])
  pyodideWorker.postMessage({type: 'patch', patch: patch, id: doc_id})
}

function loadScripts(scripts) {
  return scripts.reduce(function(cur, next){ 
    return cur.then($.getScript.bind($, next));
  }, $.when());
}

pyodideWorker.onmessage = async (event) => {
  const button = document.getElementById(`button-${event.data.id}`)
  if (event.data.type === 'loading') {
    _temporarilyChangeTooltip(button, 'Loading pyodide')
    if (window.Bokeh === undefined || window.Bokeh.Panel === undefined) {
      loadScripts({{ scripts }})
    }
  } else if (event.data.type === 'loaded') {
    _temporarilyChangeTooltip(button, 'Executing code')
  } else if (event.data.type === 'render') {
    _temporarilyChangeTooltip(button, 'Run code')
    const [view] = await Bokeh.embed.embed_item(JSON.parse(event.data.model_json))

    // Setup bi-directional syncing
    pyodideWorker.documents[event.data.id] = jsdoc = view.model.document
    jsdoc.on_change(send_change.bind(null, jsdoc, event.data.id), false)
    pyodideWorker.postMessage({'type': 'rendered', id: event.data.id})
  } else if (event.data.type === 'patch') {
    pyodideWorker.documents[event.data.id].apply_json_patch(JSON.parse(event.data.patch), event.data.buffers, setter_id='js')
  }
};

window.pyodideWorker = pyodideWorker;
