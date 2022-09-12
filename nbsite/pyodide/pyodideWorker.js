importScripts("{{ PYODIDE_URL }}");

function sendPatch(patch, buffers, cell_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers,
    id: cell_id
  })
}

async function loadApplication() {
  console.log("Loading pyodide!");
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded!");
  await self.pyodide.loadPackage("micropip");
  await self.pyodide.runPythonAsync(`
    import micropip
    await micropip.install([{{ env_spec }}]);
  `);
  console.log("Packages loaded!");
}

self.onmessage = async (event) => {
  if (event.data.type === 'render') {
    if (self.pyodide == null) {
      self.postMessage({
	type: 'loading',
	id: event.data.id
      });
      await loadApplication()
      self.postMessage({
	type: 'loaded',
	id: event.data.id
      });
    }
    const code = `
from panel import state, panel
from panel.io.pyodide import _model_json
code = """\n${event.data.code}"""
lines = code.splitlines()
exec('\\n'.join(lines[:-1]))
out = eval(lines[-1])
doc, model_json = _model_json(panel(out), 'output-${event.data.id}')
state.cache['${event.data.id}'] = doc
model_json`
    const model_json = await self.pyodide.runPythonAsync(code)
    self.postMessage({
      type: 'render',
      id: event.data.id,
      model_json: model_json
    });
  } else if (event.data.type === 'rendered') {
    self.pyodide.runPythonAsync(`
    import pyodide

    from bokeh.protocol.messages.patch_doc import process_document_events
    from panel import state

    def pysync(event):
        json_patch, buffers = process_document_events([event], use_buffers=True)
        buffer_map = {}
        for (ref, buffer) in buffers:
            buffer_map[ref['id']] = pyodide.to_js(buffer).buffer
        sendPatch(json_patch, pyodide.to_js(buffer_map), '${event.data.id}')

    doc = state.cache['${event.data.id}']
    doc.on_change(pysync)
    doc.callbacks.trigger_json_event(
        {'event_name': 'document_ready', 'event_values': {}
    })
    `)
  } else if (event.data.type === 'patch') {
    self.pyodide.runPythonAsync(`
    import json
    from panel import state
    doc = state.cache['${event.data.id}']
    doc.apply_json_patch(json.loads('${event.data.patch}'))
    `)
  }
}
