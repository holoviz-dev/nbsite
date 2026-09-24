const fs = require('node:fs');

const [pyodideURL, requirementsJSON, output] = process.argv.slice(2);
const version = pyodideURL.match(/\/v([^/]+)\/full\/pyodide\.(?:mjs|js)$/)?.[1];
if (!version) {
  throw new Error('PYODIDE_URL must point to a versioned Pyodide distribution');
}

async function main() {
  const {loadPyodide} = require(require.resolve('pyodide', {paths: [process.cwd()]}));
  const pyodide = await loadPyodide();
  if (pyodide.version !== version) {
    throw new Error(`Pyodide npm version ${pyodide.version} does not match ${version}`);
  }
  await pyodide.loadPackage('micropip');
  pyodide.globals.set('requirements', JSON.parse(requirementsJSON));
  await pyodide.runPythonAsync(`
import micropip
await micropip.install(requirements.to_py(), keep_going=True)
`);
  const lockfile = JSON.parse(pyodide.runPython('micropip.freeze()'));
  // Node's wheel cache can leave local paths in the frozen lockfile.
  for (const pkg of Object.values(lockfile.packages)) {
    if (!/^https?:\/\//.test(pkg.file_name)) {
      pkg.file_name = new URL(pkg.file_name.split('/').pop(), pyodideURL).href;
    }
  }
  fs.writeFileSync(output, JSON.stringify(lockfile));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
