/** Combine cancellation and a deadline, including runtimes without AbortSignal.any. */
export function withDeadline(signals: AbortSignal[], milliseconds: number) {
  if (typeof AbortSignal.any === 'function' && typeof AbortSignal.timeout === 'function') {
    return { signal: AbortSignal.any([...signals, AbortSignal.timeout(milliseconds)]), dispose: () => {} };
  }
  const controller = new AbortController();
  const listeners: Array<[AbortSignal, () => void]> = [];
  const dispose = () => {
    clearTimeout(timer);
    for (const [signal, listener] of listeners) signal.removeEventListener('abort', listener);
    listeners.length = 0;
  };
  const timer = setTimeout(() => {
    controller.abort(new DOMException('The operation timed out.', 'TimeoutError'));
    dispose();
  }, milliseconds);
  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      dispose();
      break;
    }
    const listener = () => {
      controller.abort(signal.reason);
      dispose();
    };
    listeners.push([signal, listener]);
    signal.addEventListener('abort', listener, { once: true });
  }
  return { signal: controller.signal, dispose };
}
