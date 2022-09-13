if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register(DOCUMENTATION_OPTIONS.URL_ROOT + 'PyodideServiceWorker.js');
}
