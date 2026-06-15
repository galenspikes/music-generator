// worker.js — runs the Pyodide engine off the main thread so long renders never
// freeze the UI. Boots on load, then answers {type:"generate"} messages with the
// rendered MIDI bytes (transferred, not copied).

import { loadPyodide } from "./pyodide/pyodide.mjs";

let py = null;
const post = (msg, transfer) => self.postMessage(msg, transfer || []);

async function boot() {
  post({ type: "status", message: "Loading Pyodide (Python → WebAssembly)…" });
  py = await loadPyodide({ indexURL: "./pyodide/" });
  post({ type: "status", message: "Loading numpy…" });
  await py.loadPackage(["numpy", "pyyaml", "packaging"]);
  post({ type: "status", message: "Loading the music engine…" });
  const buf = await (await fetch("./engine.zip")).arrayBuffer();
  py.unpackArchive(buf, "zip", { extractDir: "/engine" });
  py.runPython(`
import sys, os
sys.path.insert(0, "/engine")
os.environ["MUSICGEN_OUTPUT_DIR"] = "/out"
import music_generator as mg
def generate(args):
    args = [str(a) for a in args]
    sys.argv = ["music_generator.py", *args, "--out", "web", "--no-play"]
    return open(mg.main(), "rb").read()
`);
  post({ type: "ready" });
}

const booted = boot().catch((e) => post({ type: "fatal", message: String((e && e.message) || e) }));

self.onmessage = async (ev) => {
  const msg = ev.data;
  if (msg.type !== "generate") return;
  await booted;
  try {
    const gen = py.globals.get("generate");
    const result = gen(py.toPy(msg.args));
    const copy = result.toJs().slice();        // own ArrayBuffer for transfer
    result.destroy(); gen.destroy();
    post({ type: "result", id: msg.id, bytes: copy }, [copy.buffer]);
  } catch (e) {
    post({ type: "error", id: msg.id, message: String((e && e.message) || e) });
  }
};
