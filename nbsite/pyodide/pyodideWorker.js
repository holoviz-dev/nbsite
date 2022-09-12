importScripts("{{ PYODIDE_URL }}");

function sendPatch(patch, buffers, cell_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers,
    id: cell_id
  })
}

async function loadApplication(cell_id) {
  console.log("Loading pyodide!");
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  console.log("Loaded!");
  await self.pyodide.loadPackage("micropip");
  const packages = [{{ env_spec }}];
  await self.pyodide.runPythonAsync("import micropip")
  for (const pkg of packages) {
    self.postMessage({
      type: 'loading',
      msg: `Loading ${pkg}`,
      id: cell_id
    });
    await self.pyodide.runPythonAsync(`
      await micropip.install('${pkg}');
    `);
  }
  console.log("Packages loaded!");
}

self.onmessage = async (event) => {
  if (event.data.type === 'render') {
    if (self.pyodide == null) {
      self.postMessage({
	type: 'loading',
	msg: 'Loading pyodide',
	id: event.data.id
      });
      await loadApplication(event.data.id)
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
    try {
      const model_json = await self.pyodide.runPythonAsync(code)
      self.postMessage({
	type: 'render',
	id: event.data.id,
	model_json: model_json
      });
    } catch (e) {
      const traceback = `${e}`
      const tblines = traceback.split('\n')
      self.postMessage({
        type: 'error',
	traceback: traceback,
	msg: tblines[tblines.length-2],
	id: event.data.id
      });
    }
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
