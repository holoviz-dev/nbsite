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
  await self.pyodide.runPythonAsync("{{ setup_code }}")
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

function autodetect_deps_code(msg) {
  return `
import json
from panel.io.convert import find_imports
json.dumps(find_imports("""${msg.code}"""))
`
}

function exec_code(msg) {
   return `
from panel import state, panel
from panel.io.pyodide import _model_json
code = """\n${msg.code}"""
lines = code.splitlines()
exec('\\n'.join(lines[:-1]))
out = eval(lines[-1])
doc, model_json = _model_json(panel(out), 'output-${msg.id}')
state.cache['${msg.id}'] = doc
model_json`
}

function sync_code(msg) {
  return `
    import pyodide

    from bokeh.protocol.messages.patch_doc import process_document_events
    from panel import state

    def pysync(event):
        json_patch, buffers = process_document_events([event], use_buffers=True)
        buffer_map = {}
        for (ref, buffer) in buffers:
            buffer_map[ref['id']] = pyodide.to_js(buffer).buffer
        sendPatch(json_patch, pyodide.ffi.to_js(buffer_map), '${msg.id}')

    doc = state.cache['${msg.id}']
    doc.on_change(pysync)
    doc.callbacks.trigger_json_event(
        {'event_name': 'document_ready', 'event_values': {}
    })`
}

function patch_code(msg) {
    return `
    import json
    from panel import state
    doc = state.cache['${msg.id}']
    doc.apply_json_patch(json.loads('${msg.patch}'))`
}

const MESSAGES = {
  patch: patch_code,
  execute: exec_code,
  rendered: sync_code
}

self.onmessage = async (event) => {
  const msg = event.data

  // Init pyodide
  if (self.pyodide == null) {
    self.postMessage({
      type: 'loading',
      msg: 'Loading pyodide',
      id: msg.id
    });
    await loadApplication(msg.id)
    self.postMessage({
      type: 'loaded',
      id: msg.id
    });
  }

  // Handle message
  if (!MESSAGES.hasOwnProperty(msg.type)) {
    console.warn(`Service worker received unknown message type '${msg.type}'.`)
    return
  }

  {% if autodetect_deps %}
  if (msg.type === 'execute') {
    const deps = await self.pyodide.runPythonAsync(autodetect_deps_code(msg))
    for (const pkg of JSON.parse(deps)) {
      self.postMessage({
	type: 'loading',
	msg: `Loading ${pkg}`,
	id: msg.id
      });
      await self.pyodide.runPythonAsync(`micropip.install('${pkg}')`)
    }
  }
  {% endif %}
  
  try {
    const out = await self.pyodide.runPythonAsync(MESSAGES[msg.type](msg))
    if (out != null) {
      self.postMessage({
	type: 'render',
	id: msg.id,
	out: out
      });
    }
  } catch (e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'error',
      traceback: traceback,
      msg: tblines[tblines.length-2],
      id: msg.id
    });
    throw(e)
  }
}
