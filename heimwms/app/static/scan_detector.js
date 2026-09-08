/*
 * Keyboard-wedge barcode scan detector.
 *
 * Hardware barcode scanners in HID mode type the payload very fast and finish
 * with an Enter key. We distinguish scans from human typing by (a) an inter-
 * keystroke timeout and (b) treating Enter as an explicit terminator.
 *
 * Framework-agnostic: `createScanDetector` returns an object with a
 * `handleKey(event)` method. It calls `onScan(code)` when a full code is
 * detected. `now` is injectable for deterministic tests.
 */
(function (root) {
  function createScanDetector(options) {
    options = options || {};
    var onScan = options.onScan || function () {};
    var timeoutMs = options.timeoutMs || 50; // max gap between scanner keystrokes
    var minLength = options.minLength || 1;
    var now = options.now || function () { return Date.now(); };

    var buffer = "";
    var lastTime = 0;

    function reset() {
      buffer = "";
      lastTime = 0;
    }

    function flush() {
      var code = buffer;
      reset();
      if (code.length >= minLength) {
        onScan(code);
        return code;
      }
      return null;
    }

    function handleKey(event) {
      var t = now();
      // If the gap since the last key is too large, treat as a new sequence
      // (human typing or a fresh scan).
      if (lastTime && (t - lastTime) > timeoutMs) {
        buffer = "";
      }
      lastTime = t;

      if (event.key === "Enter") {
        return flush();
      }
      // Only accept printable single characters into the buffer.
      if (event.key && event.key.length === 1) {
        buffer += event.key;
      }
      return null;
    }

    return { handleKey: handleKey, flush: flush, reset: reset,
      _getBuffer: function () { return buffer; } };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createScanDetector: createScanDetector };
  } else {
    root.createScanDetector = createScanDetector;
  }
})(typeof window !== "undefined" ? window : this);
