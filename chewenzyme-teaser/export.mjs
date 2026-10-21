// 섹션별 PNG(2배, 가로 1440px)와 전체 한 장을 export/ 폴더에 저장
// 실행: node export.mjs   (playwright 필요)
import { chromium } from "playwright";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const dir = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch({ args: ["--disable-gpu", "--use-gl=swiftshader"] });
const page = await browser.newPage({ viewport: { width: 720, height: 1200 }, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(path.join(dir, "index.html")).href);
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(400);

for (const s of await page.locator("section[data-name]").all()) {
  const name = await s.getAttribute("data-name");
  await s.screenshot({ path: path.join(dir, "export", `chewenzyme_teaser_${name}.png`) });
}
await page.locator(".page").screenshot({ path: path.join(dir, "export", "chewenzyme_teaser_full.png") });
await browser.close();
