'use strict';
const $ = (id) => document.getElementById(id);
const sample = $('sample');
let inventory = [], coverage = new Set(), serial = 0, expanded = false;
const initialText = 'Ideas ship farther.\nBuild a brighter tomorrow.';
const features = [...document.querySelectorAll('[data-feature]')];
async function loadFace(family, weight, style = 'normal', text = 'Build a brighter tomorrow.') {
  if (!['LihuiT','zayJu'].includes(family) || Number(weight) !== 400 || style !== 'normal') throw new Error('此版本仅提供 Regular 400 正体');
  const faces = await document.fonts.load(`${style} ${weight} 64px "${family}"`, text);
  if (!faces.length || faces.some(face => face.status !== 'loaded')) throw new Error('未加载到对应的字体文件');
  return faces;
}
function checkCoverage() {
  if (!coverage.size) return;
  const missing = [...new Set([...sample.value].filter(c => !/\s/u.test(c) && !coverage.has(c.codePointAt(0))))];
  $('coverage-warning').hidden = !missing.length;
  $('coverage-warning').textContent = missing.length ? `注意：${missing.slice(0, 16).join(' ')} 不在本字体字符表内，会使用系统回退字体。当前字族不含汉字。` : '';
}
async function update() {
  const id = ++serial, family = $('family').value, weight = $('weight').value, style = $('style').value;
  const size = Number($('size').value), tracking = Number($('tracking').value) / 100;
  sample.dataset.loading = 'true';
  $('font-status').textContent = '正在加载真实字体…';
  sample.style.fontFamily = `"${family}"`;
  sample.style.fontWeight = weight;
  sample.style.fontStyle = style;
  sample.style.fontSize = `${size}px`;
  sample.style.letterSpacing = `${tracking}em`;
  sample.style.fontFeatureSettings = features.map(input => `"${input.dataset.feature}" ${Number(input.checked)}`).join(', ');
  $('size-output').textContent = `${size} px`;
  $('tracking-output').textContent = `${tracking} em`;
  try {
    await loadFace(family, weight, style);
    if (id !== serial) return;
    sample.dataset.loading = 'false';
    $('font-status').textContent = `已加载真实 WOFF2 · ${family} / ${weight} / ${style === 'normal' ? 'Upright' : 'Oblique 10°'}`;
  } catch (error) {
    if (id !== serial) return;
    $('font-status').textContent = `字体加载失败：${error.message}。没有使用系统字体冒充样张。请先运行 tools/prepare_site.py 并通过本地 HTTP 预览。`;
  }
  checkCoverage();
}
function renderGlyphs() {
  const short = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?@&';
  const selected = expanded ? inventory.filter(row => !/[\p{C}\p{Z}]/u.test(row.character)) : [...short].map(character => ({character, unicode: `U+${character.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}`}));
  const fragment = document.createDocumentFragment();
  for (const row of selected) {
    const cell = document.createElement('div'); cell.className = 'glyph';
    const character = document.createElement('span'); character.textContent = row.character;
    const caption = document.createElement('small'); caption.textContent = row.unicode;
    cell.append(character, caption); fragment.append(cell);
  }
  $('glyphs').replaceChildren(fragment);
  $('all-glyphs').textContent = expanded ? '收起完整字符表 ↑' : '查看完整字符表 ↗';
  $('all-glyphs').setAttribute('aria-expanded', String(expanded));
}
for (const id of ['family', 'weight', 'style', 'size', 'tracking']) $(id).addEventListener('input', update);
for (const input of features) input.addEventListener('change', update);
sample.addEventListener('input', checkCoverage);
for (const button of document.querySelectorAll('[data-sample]')) button.addEventListener('click', () => {sample.value = button.dataset.sample; checkCoverage(); sample.focus();});
for (const button of document.querySelectorAll('.choose-family')) button.addEventListener('click', () => {$('family').value = button.dataset.family; update(); $('playground').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});});
$('reset').addEventListener('click', () => {sample.value = initialText; $('family').value = 'zayJu'; $('weight').value = '400'; $('style').value = 'normal'; $('size').value = innerWidth < 640 ? '36' : '64'; $('tracking').value = '0'; features.forEach(input => input.checked = input.dataset.feature === 'liga'); update();});
$('all-glyphs').addEventListener('click', () => {expanded = !expanded; renderGlyphs();});
$('theme').addEventListener('click', () => {const dark = document.documentElement.dataset.theme !== 'dark'; document.documentElement.dataset.theme = dark ? 'dark' : 'light'; $('theme').setAttribute('aria-pressed', String(dark)); $('theme').setAttribute('aria-label', dark ? '切换浅色模式' : '切换深色模式');});
async function init() {
  if (innerWidth < 640) $('size').value = '36';
  sample.dataset.loading = 'true';
  const results = await Promise.allSettled([...document.querySelectorAll('.specimen')].map(async element => {await loadFace(element.dataset.font, element.dataset.weight, 'normal', element.textContent); element.classList.add('font-loaded');}));
  if (results.some(result => result.status === 'rejected')) document.querySelector('.release-notice').textContent = '部分真实字体加载失败。请先构建并准备站点；没有使用系统字体冒充缺失样张。';
  try {
    const response = await fetch('characters.json'); if (!response.ok) throw new Error('字符表不可用');
    inventory = await response.json(); coverage = new Set(inventory.map(row => Number.parseInt(row.unicode.slice(2), 16)));
    document.querySelectorAll('[data-codepoints]').forEach(element => element.textContent = String(inventory.length));
    await loadFace('zayJu', 400); renderGlyphs();
  } catch (error) {$('glyphs').textContent = `字符表未加载：${error.message}`; $('all-glyphs').disabled = true;}
  await update();
}
init().catch(error => {$('font-status').textContent = `预览初始化失败：${error.message}`;});
