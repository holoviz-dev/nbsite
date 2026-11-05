const fs = require('node:fs');
const path = require('node:path');

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
  const requirements = JSON.parse(requirementsJSON);
  const localWheels = new Map();
  for (const [index, requirement] of requirements.entries()) {
    if (!requirement.endsWith('.whl') || /^[a-z]+:\/\//i.test(requirement)) {
      continue;
    }
    const wheelPath = path.resolve(path.dirname(output), '..', requirement);
    const wheelName = path.basename(wheelPath);
    const emfsPath = `/tmp/${wheelName}`;
    pyodide.FS.writeFile(emfsPath, fs.readFileSync(wheelPath));
    requirements[index] = `emfs:${emfsPath}`;
    localWheels.set(wheelName, path.posix.normalize(`../${requirement}`));
  }
  pyodide.globals.set('requirements', requirements);
  await pyodide.runPythonAsync(`
import micropip
await micropip.install(requirements.to_py(), keep_going=True)
`);
  const lockfile = JSON.parse(pyodide.runPython('micropip.freeze()'));
  const imports = JSON.parse(pyodide.runPython(`
import importlib.metadata
import json
json.dumps(importlib.metadata.packages_distributions())
`));
  for (const [module, distributions] of Object.entries(imports)) {
    for (const distribution of distributions) {
      const pkg = lockfile.packages[distribution.toLowerCase().replace(/_/g, '-')];
      if (pkg && pkg.file_name.endsWith('.whl') && !pkg.imports.includes(module)) {
        pkg.imports.push(module);
      }
    }
  }
  // Panel and panel-material-ui depend on each other, which stalls loadPackage.
  if (lockfile.packages.panel?.depends.includes('panel-material-ui')) {
    const materialDeps = lockfile.packages['panel-material-ui']?.depends;
    if (materialDeps?.includes('panel')) {
      materialDeps.splice(materialDeps.indexOf('panel'), 1);
    }
  }
  // Node's wheel cache can leave local paths in the frozen lockfile.
  for (const pkg of Object.values(lockfile.packages)) {
    const wheelName = pkg.file_name.split('/').pop();
    if (localWheels.has(wheelName)) {
      pkg.file_name = localWheels.get(wheelName);
    } else if (!/^https?:\/\//.test(pkg.file_name)) {
      pkg.file_name = new URL(pkg.file_name.split('/').pop(), pyodideURL).href;
    }
  }
  fs.writeFileSync(output, JSON.stringify(lockfile));
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
