---
release type: patch
---
The built-in toolbar script is now compatible with django-debug-toolbar 7.0.0,
which renders the toolbar inside a shadow DOM by default.

Previously, all DOM queries targeted `#djDebug` directly on the document,
which broke under shadow DOM isolation — `querySelector` cannot pierce a shadow
boundary.

Using a `getDebugElement()` helper that locates `#djDebug` via
the shadow root of its host element (`#djDebugRoot`):

```js
function getDebugElement() {
  const root = document.getElementById("djDebugRoot");
  if (root) {
    return (root.shadowRoot || root).querySelector("#djDebug");
  }
  return document.getElementById("djDebug");
}
```

This also handles the `USE_SHADOW_DOM = False` fallback gracefully, keeping
backward compatibility with older versions of the toolbar.
