importScripts("{{ PYODIDE_URL }}");

const QUEUE = [];

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
function sendStderr(cell_id, stderr) {
  self.postMessage({
    type: 'stderr',
    content: stderr,
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
  self.pyodide.runPython("import micropip")
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
  const escaped = msg.code.replace(/"""/g, '\\"\\"\\"');
  return `
import json
from panel.io.mime_render import find_imports
code = r"""\n${escaped}""".replace(r'\\"\\"\\"', '"""')
json.dumps(find_imports(code))`
}

function exec_code(msg) {
  const escaped = msg.code.replace(/"""/g, '\\"\\"\\"');
  return `
from functools import partial
from panel.io.pyodide import pyrender
from js import console

code = r"""\n${escaped}""".replace(r'\\"\\"\\"', '"""')
stdout_cb = partial(sendStdout, '${msg.id}')
stderr_cb = partial(sendStderr, '${msg.id}')
target = 'output-${msg.id}'
pyrender(code, stdout_cb, stderr_cb, target)`
}

function onload_code(msg) {
  return `
if '${msg.mime}' == 'application/bokeh':
    from panel.io.pyodide import _link_docs_worker
    from panel.io.state import state
    doc = state.cache['output-${msg.id}']
    _link_docs_worker(doc, sendPatch, '${msg.id}', 'js')
`}

function patch_code(msg) {
    return `
import json
from panel import state
doc = state.cache['output-${msg.id}']
doc.apply_json_patch(json.loads('${msg.patch}'), setter='js')`
}

const MESSAGES = {
  patch: patch_code,
  execute: exec_code,
  rendered: onload_code
}

self.onmessage = async (event) => {
  let resolveExecution, rejectExecution;
   const executing = new Promise(function(resolve, reject){
    resolveExecution = resolve;
    rejectExecution = reject;
  });
  
  const prev_msg = QUEUE[0]
  const msg = {...event.data, executing}
  QUEUE.unshift(msg)

  if (prev_msg) {
    self.postMessage({
      type: 'loading',
      msg: 'Awaiting previous cells',
      id: msg.id
    });
    await prev_msg.executing
  }

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
    self.postMessage({
      type: 'idle',
      id: msg.id
    });
    return
  }

  {% if autodetect_deps %}
  if (msg.type === 'execute') {
    let deps
    try {
      deps = self.pyodide.runPython(autodetect_deps_code(msg))
    } catch(e) {
      deps = '[]'
      console.warn(`Auto-detection of dependencies failed with error: ${e}`)
    }
    for (const pkg of JSON.parse(deps)) {
      self.postMessage({
        type: 'loading',
        msg: `Loading ${pkg}`,
        id: msg.id
      });
      try {
	await self.pyodide.runPythonAsync(`await micropip.install('${pkg}')`)
      } catch(e) {
	console.log(`Auto-detected dependency ${pkg} could not be installed.`)
      }
    }
  }
  {% endif %}
  
  try {
    let out = await self.pyodide.runPythonAsync(MESSAGES[msg.type](msg))
    resolveExecution()
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
      id: msg.id,
      uuid: msg.uuid
    });
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
