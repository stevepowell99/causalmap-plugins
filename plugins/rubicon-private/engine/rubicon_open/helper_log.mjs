// The plugin's hook on SubagentStart and SubagentStop: while a second reading is open (`isolation.OPEN` in the plugin's
// data folder, which `isolate.py open` writes), it notes each helper that starts or stops, with the path of the
// transcript Claude Code keeps of it, for `isolate.py close` to read. It runs for every helper of every session, Rubicon
// run or not, so it looks for that list before doing anything else and returns at once without it. It never blocks:
// it prints nothing, catches every error and always exits 0. It is Node, which the engine already needs, so one command
// runs alike in Git Bash, sh and PowerShell, whichever names Python goes by.
//     node helper_log.mjs <plugin data folder> <SubagentStart|SubagentStop>
import fs from "node:fs";
import path from "node:path";

const STALE_MS = 2 * 24 * 3600 * 1000; // isolation.STALE_MS
const [, , data, event] = process.argv;
let open;
try {
  open = JSON.parse(fs.readFileSync(path.join(data, "isolating.json"), "utf8"));
} catch {
  process.exit(0);
}
try {
  const hook = JSON.parse(fs.readFileSync(0, "utf8") || "{}");
  if (!hook.agent_id) process.exit(0); // a note that names no helper says nothing close could use
  const now = Date.now();
  const note = JSON.stringify({
    event, at: now, agent_id: hook.agent_id ?? null, agent_type: hook.agent_type ?? null,
    agent_transcript_path: hook.agent_transcript_path ?? null, transcript_path: hook.transcript_path ?? null,
    session_id: hook.session_id ?? null, cwd: hook.cwd ?? null,
  });
  for (const run of Object.values(open.runs || {})) {
    if (!run || !run.events || now - run.opened > STALE_MS) continue;
    fs.mkdirSync(run.events, { recursive: true });
    fs.writeFileSync(path.join(run.events, `${now}-${process.pid}-${event}-${hook.agent_id ?? "none"}.json`), note);
  }
} catch {
  // a note that cannot be written leaves the log partial, which close reports; the helper is never held up
}
process.exit(0);
