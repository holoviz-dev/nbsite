/**
 * SVG files for our copy buttons
 */
let iconRun = `<svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-check" width="44" height="44" viewBox="0 0 24 24" stroke-width="2" stroke="#22863a" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <title>${messages[locale]['copy_success']}</title>
  <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
  <path d="M5 12l5 5l10 -10" />
</svg>`

/**
 * Set up run for code blocks
 */

const _runWhenDOMLoaded = cb => {
  if (document.readyState != 'loading') {
    cb()
  } else if (document.addEventListener) {
    document.addEventListener('DOMContentLoaded', cb)
  } else {
    document.attachEvent('onreadystatechange', function() {
      if (document.readyState == 'complete') cb()
    })
  }
}

const _codeCellId = index => `codecell${index}`

// Changes tooltip text for two seconds, then changes it back
const _temporarilyChangeTooltip = (el, newText, timeout) => {
  const oldText = el.getAttribute('data-tooltip')
  el.setAttribute('data-tooltip', newText)
  if (timeout != null) {
    setTimeout(() => el.setAttribute('data-tooltip', oldText), timeout)
  }
}

// Changes the copy button icon for two seconds, then changes it back
const _temporarilyChangeIcon = (el) => {
  el.innerHTML = iconCheck;
  setTimeout(() => {el.innerHTML = iconCopy}, 2000)
}

const _addRunButtonToCodeCells = () => {
  // If Pyodide Worker hasn't loaded, wait a bit and try again.
  if (window.pyodideWorker === undefined) {
    setTimeout(addRunButtonToCodeCells, 250)
    return
  }

  // Add copybuttons to all of our code cells
  const RUNBUTTON_SELECTOR = 'div.highlight pre';
  const codeCells = document.querySelectorAll(RUNBUTTON_SELECTOR)
  codeCells.forEach((codeCell, index) => {
    const id = _codeCellId(index)
    codeCell.setAttribute('id', id)

    const RunButton = id =>
    `<button id="button-${id}" class="runbtn o-tooltip--left" data-tooltip="Run cell" data-clipboard-target="#${id}">
      ${iconRun}
    </button>`
    codeCell.insertAdjacentHTML('afterend', RunButton(id))
    const run_button = document.getElementById(`button-${id}`)
    run_button.onclick = () => {
      let output = document.getElementById(`output-${id}`)
      if (output == null) {
	const output = document.createElement('div');
	output.setAttribute('id', `output-${id}`)
	codeCell.parentElement.parentElement.appendChild(output)
      } else {
	output.innerHTML = ''
      }
      window.pyodideWorker.postMessage({
	type: 'render',
	id: id,
	code: codeCell.textContent
      })
    }
  })
}

_runWhenDOMLoaded(_addRunButtonToCodeCells)
