// 搁架的后台：让一个 AI（或者任何会写文件的东西）往搁架上放照片、让照片偶尔自己掉下来一张。
// The shelf's back room: lets an AI keep photos on the shelf, and lets a photo fall off now and then.
//
// 零依赖，Node 18+。两种用法：
//   1) 直接跑：node server/keeper.mjs [端口]  —— 静态服务 + photos/ 一有新照片就自动重烤
//   2) 当模块：import { keepHint, keepPhoto, KEEP_TOOL, shelfBump, ensureFresh } from "./server/keeper.mjs"
//      接进你自己的聊天后台（怎么接见 docs/how-it-lives.md）
import fs from "fs";
import path from "path";
import http from "http";
import { spawn } from "child_process";
import { fileURLToPath } from "url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const PHOTOS = path.join(ROOT, "photos");
const IMG = /\.(jpe?g|png|webp|gif)$/i;

// ── 标签：定一小套，不够再添。几个地方（几扇聊天窗、半夜醒着的那一趟）各起各的名，搁架就乱了 ──
// Keep the tag set small and shared, or every conversation will invent its own names.
export const TAGS = ["人", "我", "吃的", "地方", "外面", "猫", "画", "截图"];

// ── 1. 对方发来一张图时，塞给 AI 的那句提醒 ──────────────────────────────
// 不是命令它存：留不留由它自己挑。这一句挂在那一轮的消息后面就行。
// When an image arrives in chat, append this to the AI's turn. It is an invitation, not an order.
export function keepHint(srcPath, { tags = TAGS, dir = PHOTOS } = {}) {
  return `[对方发来一张图片，存在 ${srcPath}。先看它再回应。` +
    `若这张你真想留住（不是每张都留，由心），复制进 ${dir}${path.sep}，再写一个同名 .txt：说一句为什么留；` +
    `最后一行写「标签：${tags.slice(0, 2).join(" · ")}」（从 ${tags.join("/")} 里挑，可挂几个，都不合适才开新的）。那是搁架，对方看得到。]`;
}

// ── 2. 给只会调工具、碰不到文件的 AI：一个「放上搁架」的工具 ─────────────
// For models that call tools instead of writing files: the tool schema, and its implementation.
export const KEEP_TOOL = {
  name: "keep_on_shelf",
  description: "把一张图放上搁架：复制进 photos/，写上为什么留、贴标签。不是每张都要留，只留你真想留的。",
  input_schema: {
    type: "object",
    properties: {
      src: { type: "string", description: "图片现在的路径" },
      why: { type: "string", description: "为什么留它，写给对方看，会印在照片背面" },
      tags: { type: "array", items: { type: "string" }, description: "从标签那一小套里挑，可多选" },
      date: { type: "string", description: "可选，YYYY-MM-DD；不填就用今天" },
    },
    required: ["src", "why"],
  },
};
export function keepPhoto({ src, why = "", tags = [], date } = {}, dir = PHOTOS) {
  if (!src || !fs.existsSync(src)) throw new Error("找不到这张图: " + src);
  if (!IMG.test(src)) throw new Error("不是图片: " + src);
  fs.mkdirSync(dir, { recursive: true });
  const now = new Date(), pad = (n) => String(n).padStart(2, "0");
  const day = /^\d{4}(-\d{2}){0,2}$/.test(date || "") ? date : `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;   // 本地日期，不用 UTC（东边的时区清早还是 UTC 的昨天）
  const stem = day + "_" + path.parse(src).name.replace(/[^\p{L}\p{N}_-]+/gu, "-").slice(0, 60);
  let name = stem + path.extname(src).toLowerCase(), k = 2;
  while (fs.existsSync(path.join(dir, name))) name = `${stem}-${k++}${path.extname(src).toLowerCase()}`;
  fs.copyFileSync(src, path.join(dir, name));
  const tagLine = tags.length ? `\n标签：${[...new Set(tags)].join(" · ")}` : "";
  fs.writeFileSync(path.join(dir, path.parse(name).name + ".txt"), String(why).trim() + tagLine + "\n");
  ensureFresh().catch(() => {});
  return { file: name };
}

// ── 3. 撞见：屋里没人的时候，搁架上自己掉下来一张 ──────────────────────
// 挂在你的「保活」「定时醒来」那种没人说话的轮次上：隔一阵、掷一次，掉下来一张，连同当初写的为什么留。
// 你把图原样放进聊天窗（对方回来看得见掉的是哪张），把 why 给 AI 看；它有话就接一句，没有就沉默。不推送。
// "Bump": on idle turns (keep-alive, scheduled wake-ups), now and then a photo falls off the shelf,
// together with the note written when it was kept. Show it in the chat; let the AI say something or nothing.
export function shelfBump({ dir = PHOTOS, state = path.join(ROOT, ".bump.json"), everyMs = 2 * 3600e3, chance = .5 } = {}) {
  let last = 0;
  try { last = JSON.parse(fs.readFileSync(state, "utf8")).at || 0; } catch {}
  if (Date.now() - last < everyMs || Math.random() > chance) return null;
  const all = fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => IMG.test(f)) : [];
  if (!all.length) return null;
  const file = all[Math.floor(Math.random() * all.length)];
  let why = "";
  try { why = fs.readFileSync(path.join(dir, file.replace(/\.[^.]+$/, ".txt")), "utf8").trim().replace(/\n?[ \t]*(标签|tags?)[:：][^\n]*$/i, "").trim(); } catch {}
  fs.writeFileSync(state, JSON.stringify({ at: Date.now(), file }));
  return { file, path: path.join(dir, file), why };
}
// 撞见时给 AI 的那段话（照搬我们家用的写法）
export function bumpNote(b) {
  return `<撞见 说明="没人叫你看。屋里没人的时候，搁架上自己掉下来一张">\n${b.path}\n` +
    (b.why ? `（当初留它时写的：${b.why.slice(0, 300)}）` : "（这张没配字）") +
    `\n想看就看一眼，不想就算了；看完有话就说一句，会接在那张图底下；没有就沉默。\n</撞见>`;
}

// ── 4. 新照片进来自动重烤（一分钟最多一次；photos/ 比 photos.json 新才烤） ─────────
let baking = null, bakedAt = 0;
function newestIn(dir) { let t = 0; try { for (const f of fs.readdirSync(dir)) t = Math.max(t, fs.statSync(path.join(dir, f)).mtimeMs) } catch {} return t; }
export function ensureFresh({ python = process.env.PYTHON || "python" } = {}) {
  const json = path.join(ROOT, "photos.json");
  const stale = !fs.existsSync(json) || newestIn(PHOTOS) > fs.statSync(json).mtimeMs;
  if (!stale) return Promise.resolve(false);
  if (baking) return baking;
  if (Date.now() - bakedAt < 60e3) return Promise.resolve(false);
  bakedAt = Date.now();
  baking = new Promise((ok) => {
    const cp = spawn(python, [path.join(ROOT, "tools", "bake.py")], { cwd: ROOT, stdio: "ignore", windowsHide: true });
    cp.on("error", (e) => { console.error("[keeper] 烤不了（装了 Python、pillow、numpy 吗）:", e.message); ok(false) });
    cp.on("exit", () => ok(true));
  }).finally(() => { baking = null });
  return baking;
}

// ── 直接跑：静态服务 ──
const TYPES = { ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".md": "text/markdown; charset=utf-8" };
export function serve(port = 8000) {
  return http.createServer(async (req, res) => {
    let p;
    try { p = decodeURIComponent(new URL(req.url, "http://x").pathname) } catch { res.writeHead(400); return res.end("bad url") }
    if (p === "/") p = "/index.html";
    if (p === "/photos.json") await Promise.race([ensureFresh(), new Promise((r) => setTimeout(r, 20e3))]);
    const f = path.join(ROOT, path.normalize(p).replace(/^([/\\])+/, ""));
    if (!f.startsWith(ROOT) || /[/\\]\.|[/\\]server[/\\]/.test(f.slice(ROOT.length)) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end("not found") }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(f).toLowerCase()] || "application/octet-stream", "Cache-Control": p === "/photos.json" ? "no-cache" : "max-age=3600" });
    fs.createReadStream(f).pipe(res);
  }).listen(port, () => console.log(`搁架在 http://localhost:${port}`));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) serve(+process.argv[2] || 8000);
