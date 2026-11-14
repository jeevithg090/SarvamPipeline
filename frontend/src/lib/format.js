/** Format a number of seconds as m:ss (or h:mm:ss past an hour). */
export function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = String(s % 60).padStart(2, '0');
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, '0')}:${seconds}`;
  return `${minutes}:${seconds}`;
}

/** Plain-text version of the transcript, one "Speaker: text" line per turn. */
export function transcriptToText(turns) {
  return turns.map((t) => `${t.role === 'user' ? 'You' : 'Agent'}: ${t.content}`).join('\n');
}
