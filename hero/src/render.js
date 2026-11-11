// Frame-accurate renderer: drives window.renderFrame(t) in headless Chromium and
// pipes PNG frames into ffmpeg.
//
//   node render.js <scene.html> <out-basename> [--fps=30] [--w=854 --h=480] [--from=0 --to=3.6] [--bg=light]
//   node render.js <scene.html> <out-dir> --stills=0.5,2,4   (PNG stills only)
//
// Produces <out>.webm (VP9) and <out>.mp4 (H.264, for Safari/iOS) plus <out>-poster.jpg.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const http = require("http");

// tiny static server (ES modules + import maps don't load from file://)
function serve(root) {
  const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".woff2": "font/woff2" };
  return new Promise(res => {
    const srv = http.createServer((req, rsp) => {
      const f = path.join(root, decodeURIComponent(req.url.split("?")[0]));
      if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { rsp.writeHead(404); return rsp.end(); }
      rsp.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" });
      fs.createReadStream(f).pipe(rsp);
    }).listen(0, "127.0.0.1", () => res(srv));
  });
}

const args = process.argv.slice(2);
const opt = Object.fromEntries(args.filter(a => a.startsWith("--")).map(a => {
  const [k, v] = a.slice(2).split("="); return [k, v ?? "1"];
}));
const [scene, out] = args.filter(a => !a.startsWith("--"));
const FPS = +(opt.fps || 30);
const W = +(opt.w || 1920), H = +(opt.h || 1080);

const run = (cmd, argv, input) => new Promise((res, rej) => {
  const p = spawn(cmd, argv, { stdio: [input ? "pipe" : "ignore", "inherit", "inherit"] });
  p.on("exit", c => (c === 0 ? res() : rej(new Error(`${cmd} exited ${c}`))));
  if (input) input(p.stdin);
});

(async () => {
  const q = new URLSearchParams();
  if (opt.w) q.set("w", opt.w);
  if (opt.h) q.set("h", opt.h);
  if (opt.bg) q.set("bg", opt.bg);
  const root = path.dirname(path.resolve(scene));
  const srv = await serve(root);
  const url = `http://127.0.0.1:${srv.address().port}/${path.basename(scene)}?${q}`;

  const browser = await chromium.launch({ args: ["--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on("pageerror", e => console.error("[page]", e.message));
  page.on("console", m => { if (m.type() === "error") console.error("[console]", m.text()); });
  await page.goto(url);
  await page.waitForFunction(() => window.sceneReady, null, { timeout: 60000 });
  await page.evaluate(() => window.sceneReady);
  const dur = await page.evaluate(() => window.DURATION);

  if (opt.stills) {
    fs.mkdirSync(out, { recursive: true });
    for (const t of opt.stills.split(",").map(Number)) {
      await page.evaluate(t => window.renderFrame(t), t);
      await page.screenshot({ path: path.join(out, `t${t.toFixed(2)}.png`) });
    }
    await browser.close(); srv.close();
    return;
  }

  const t0 = +(opt.from || 0), t1 = Math.min(dur, +(opt.to || dur));
  const frames = Math.round((t1 - t0) * FPS);
  const raw = out + ".master.mov";
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
    "-c:v", "qtrle", raw], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((res, rej) => ff.on("exit", c => (c === 0 ? res() : rej(new Error("ffmpeg " + c)))));
  for (let i = 0; i < frames; i++) {
    await page.evaluate(t => window.renderFrame(t), t0 + i / FPS);
    const buf = await page.screenshot({ type: "png" });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (i % 30 === 0) process.stdout.write(`frame ${i}/${frames}\r`);
  }
  ff.stdin.end();
  await done;
  await browser.close(); srv.close();
  console.log(`\nmaster written (${frames} frames)`);

  // VP9 WebM (2-pass, constrained quality)
  const vp9 = ["-i", raw, "-c:v", "libvpx-vp9", "-b:v", "2600k", "-maxrate", "3800k", "-crf", "28",
    "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", "-pix_fmt", "yuv420p", "-an"];
  await run("ffmpeg", ["-v", "error", "-y", ...vp9, "-pass", "1", "-passlogfile", out, "-f", "webm", "/dev/null"]);
  await run("ffmpeg", ["-v", "error", "-y", ...vp9, "-pass", "2", "-passlogfile", out, out + ".webm"]);
  // H.264 MP4 fallback (Safari / iOS)
  await run("ffmpeg", ["-v", "error", "-y", "-i", raw, "-c:v", "libx264", "-preset", "slow", "-crf", "24",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", out + ".mp4"]);
  // poster = fully-revealed frame
  await run("ffmpeg", ["-v", "error", "-y", "-ss", String(Math.max(0, (t1 - t0) - 1.2)), "-i", raw,
    "-frames:v", "1", "-q:v", "3", out + "-poster.jpg"]);
  for (const f of fs.readdirSync(path.dirname(out)))
    if (f.startsWith(path.basename(out)) && f.endsWith(".log")) fs.unlinkSync(path.join(path.dirname(out), f));
  fs.unlinkSync(raw);
  console.log("done:", out);
})().catch(e => { console.error(e); process.exit(1); });
