/** Validation, recovery and consent precede the only synchronous workspace commit.
 * The host guard must bind the match, settings, lifecycle and request generation.
 * No raw recording or private runtime Agent is passed to the consent UI. */
export type RecordingTransitionPort = {
  guard(): () => void;
  unfinished(): boolean;
  save(): Promise<boolean>;
  confirm(saved: boolean): Promise<boolean>;
  dismissPrompt(): void;
};

export class RecordingTransitions {
  constructor(private port: RecordingTransitionPort) {}

  async open<T>(prepare: () => T | Promise<T>, commit: (recording: T) => void, requested = () => {}) {
    this.port.dismissPrompt();
    const guard = this.port.guard();
    const check = () => { guard(); requested(); };
    check();
    const recording = await prepare();
    check();
    if (this.port.unfinished()) {
      // A failed save is a visible recovery limitation, not permission to claim
      // success or silently enable saving after the user opted out.
      const saved = await this.port.save().catch(() => false);
      check();
      const accepted = await this.port.confirm(saved);
      check();
      if (!accepted) return false;
    }
    check();
    commit(recording);
    return true;
  }
}

export const recordingRecoveryMessage = (saved: boolean) => saved
  ? "Saved in Recent matches on this device. Use Resume when available, or Replay. No cloud backup."
  : "Device saving is off, unavailable, or could not keep this match. Download it before opening the recording if you need a copy.";

export function recordingError(context: string, error: unknown) {
  const message = error instanceof Error ? error.message : "Invalid recording.";
  return `${context} rejected: ${message === "The agent returned an illegal move. The match is paused." ? "The recording contains an illegal move." : message}`;
}

export const recordingDialogMarkup = `<dialog id="recording-dialog" aria-labelledby="recording-title" aria-describedby="recording-description recording-recovery">
  <form method="dialog">
    <h2 id="recording-title">Open this recording?</h2>
    <p id="recording-description">This replaces your unfinished match in the arena.</p>
    <p id="recording-recovery" class="muted"></p>
    <p id="recording-transfer-status" class="muted" role="status"></p>
    <div class="recording-actions">
      <button id="keep-current-match" value="keep" autofocus>Keep playing</button>
      <button id="download-current-match" type="button">Download current match</button>
      <button id="open-recording" value="open">Open recording</button>
    </div>
  </form>
</dialog>`;
