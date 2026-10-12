const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// Uso: NODE_PATH="<pasta-com-node_modules>" node render.cjs
// Gera instagram/slide-01.png ... em 1080x1350.
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 } });

  const htmlPath = path.resolve(__dirname, 'carrossel.html');
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);

  const outputDir = path.join(__dirname, 'instagram');
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir);

  const slides = await page.$$('.slide');
  for (let i = 0; i < slides.length; i++) {
    const num = String(i + 1).padStart(2, '0');
    await slides[i].screenshot({ path: path.join(outputDir, `slide-${num}.png`) });
    console.log(`slide-${num}.png`);
  }

  await browser.close();
  console.log(`Pronto: ${slides.length} slides em instagram/ (1080x1350)`);
})();
