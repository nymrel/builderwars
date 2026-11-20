/* One optional device checkpoint; the existing agency replay remains authority. */
(function (root) {
  'use strict';
  const A = root.AgentworldAgency, E = root.Agentworld;
  const KEY = 'builderwars.agency.return.v1';
  function bounded(text) {
    if (typeof text !== 'string' || new TextEncoder().encode(text).length > E.MAX_BYTES)
      throw Error('The saved visit exceeds the supported size. Export your current visit.');
    return text;
  }
  function createStore(storage) {
    const port = () => typeof storage === 'function' ? storage() : storage;
    function load() {
      let raw;
      try {
        raw = port().getItem(KEY);
        return { raw, session: raw === null ? null : A.verify(bounded(raw)), error: null };
      } catch {
        return { raw, session: null, error: 'The saved visit could not be verified or device storage is unavailable. It has not been replaced.' };
      }
    }
    function unchanged(expected) {
      if (expected === undefined || port().getItem(KEY) !== expected)
        throw Error('The saved visit changed in another tab. Your current visit is still here; export it before replacing anything.');
    }
    function save(session, expected) {
      const raw = bounded(JSON.stringify(A.pack(session)));
      A.verify(raw);
      unchanged(expected);
      port().setItem(KEY, raw);
      if (port().getItem(KEY) !== raw) throw Error('Device saving could not be confirmed. Export this visit to keep it.');
      return raw;
    }
    function forget(expected) {
      unchanged(expected);
      port().removeItem(KEY);
      if (port().getItem(KEY) !== null) throw Error('Removing the saved visit could not be confirmed.');
    }
    return Object.freeze({ load, save, forget });
  }
  root.AgentworldReturn = Object.freeze({ KEY, createStore });
})(globalThis);
