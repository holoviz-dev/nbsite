importScripts("{{ PYODIDE_URL }}");

let EXECUTING = null;

function sendPatch(patch, buffers, cell_id) {
  self.postMessage({
    type: 'patch',
    patch: patch,
    buffers: buffers,
    id: cell_id
  })
}

function sendStdout(cell_id, stdout) {
  self.postMessage({
    type: 'stdout',
    content: stdout,
    id: cell_id
  })
}
function sendStderr(cell_id, stdout) {
  self.postMessage({
    type: 'stderr',
    content: stdout,
    id: cell_id
  })
}

async function loadApplication(cell_id) {
  console.log("Loading pyodide!");
  self.pyodide = await loadPyodide();
  self.pyodide.globals.set("sendPatch", sendPatch);
  self.pyodide.globals.set("sendStdout", sendStdout);
  self.pyodide.globals.set("sendStderr", sendStderr);
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
json.dumps(find_imports("""${msg.code}"""))`
}

function exec_code(msg) {
   return `
from functools import partial
from panel.io.pyodide import pyrender

code = """\n${msg.code}"""
stdout_cb = partial(sendStdout, '${msg.id}')
stderr_cb = partial(sendStderr, '${msg.id}')
target = 'output-${msg.id}'
pyrender(code, stdout_cb, stderr_cb, target)`
}

function onload_code(msg) {
  return `
if '${msg.mime}' == 'application/bokeh':
    from panel import state
    from panel.io.pyodide import _link_docs_worker
    doc = state.cache['output-${msg.id}']
    _link_docs_worker(doc, sendPatch, '${msg.id}')`
}

function patch_code(msg) {
    return `
import json
from panel import state
doc = state.cache['output-${msg.id}']
doc.apply_json_patch(json.loads('${msg.patch}'))`
}

const MESSAGES = {
  patch: patch_code,
  execute: exec_code,
  rendered: onload_code
}

self.onmessage = async (event) => {
  const msg = event.data

  if (EXECUTING != null) {
    self.postMessage({
      type: 'loading',
      msg: 'Awaiting previous cells',
      id: msg.id
    });
    await EXECUTING
  }

  let resolveExecution, rejectExecution;
  EXECUTING = new Promise(function(resolve, reject){
    resolveExecution = resolve;
    rejectExecution = reject;
  });

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
    resolveExecution()
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
    let out = await self.pyodide.runPythonAsync(MESSAGES[msg.type](msg))
    if (out == null) {
      out = new Map()
    }
    if (out.has('content')) {
      self.postMessage({
        type: 'render',
        id: msg.id,
        content: out.get('content'),
        mime: out.get('mime_type')
      });
    }
    if (out.has('stdout') && out.get('stdout').length) {
      self.postMessage({
        type: 'stdout',
        content: out.get('stdout'),
        id: msg.id
      });
    }
    if (out.has('stderr') && out.get('stderr').length) {
      self.postMessage({
        type: 'stderr',
        content: out.get('stderr'),
        id: msg.id
      });
    }
    self.postMessage({
      type: 'idle',
      id: msg.id
    });
    resolveExecution()
  } catch (e) {
    const traceback = `${e}`
    const tblines = traceback.split('\n')
    self.postMessage({
      type: 'error',
      traceback: traceback,
      msg: tblines[tblines.length-2],
      id: msg.id
    });
    resolveExecution()
    throw(e)
  }
}
