// Runs the built Vue app against an isolated mock HTTP server, using only Node and Chromium.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dist = path.join(root, 'webui/dist');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64');
const config = {
  default_model: 'configured-image-model', models: ['configured-image-model', 'another-model'],
  sizes: ['auto', '1024x1024', '1536x1024', '1024x1536'], qualities: ['auto', 'low', 'medium', 'high'],
  formats: ['png', 'jpeg', 'webp'], backgrounds: ['auto', 'transparent', 'opaque'], moderations: ['auto', 'low'],
  input_fidelities: ['low', 'high'], styles: ['natural', 'vivid'], response_formats: ['b64_json', 'url'],
  max_n: 2, max_prompt_length: 32000,
};
const oldImage = {
  id: 'history-1', type: 'generate', filename: 'sample.png', url: '/outputs/sample.png',
  prompt: 'Synthetic old record', model: 'old-model', size: '1024x1024', quality: 'auto', format: 'png',
  created_at: '2026-01-01T00:00:00Z',
};
const state = { images: [oldImage], jobs: [], submissions: [], edits: [], apiPaths: [] };
let pendingEdit;
const respond = (res, body, status = 200) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(body)); };
const server = http.createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const route = pathname.replace(/^\/workshop\/imagen(?=\/)/, '');
    if (route.startsWith('/api/')) state.apiPaths.push(pathname);
    const chunks = []; for await (const chunk of req) chunks.push(chunk);
    const bytes = Buffer.concat(chunks);
    if (route === '/api/config') return respond(res, config);
    if (route === '/api/images') return respond(res, { images: state.images });
    if (route === '/api/jobs/active') return respond(res, { job: state.jobs.find(job => ['running', 'queued'].includes(job.status)) ?? null });
    if (route === '/api/jobs' && req.method === 'GET') return respond(res, { jobs: state.jobs });
    if (route === '/api/jobs' && req.method === 'POST') {
      const submitted = JSON.parse(bytes.toString());
      state.submissions.push(submitted);
      const job = { id: `job-${state.submissions.length}`, ...submitted, status: 'running', images: [], error_fields: {},
        options: { ...submitted.options, model: submitted.options.model || config.default_model },
        created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
      state.jobs.unshift(job); return respond(res, { job });
    }
    if (route.startsWith('/api/jobs/')) return respond(res, { job: state.jobs.find(job => job.id === route.slice(10)) });
    if (route === '/api/edit' && req.method === 'POST') {
      const boundary = req.headers['content-type'].split('boundary=')[1];
      const entries = bytes.toString('latin1').split(`--${boundary}`).flatMap(part => {
        const split = part.indexOf('\r\n\r\n'); if (split < 0) return [];
        const headers = part.slice(0, split), body = Buffer.from(part.slice(split + 4, -2), 'latin1');
        const name = /name="([^"]+)"/.exec(headers)?.[1], filename = /filename="([^"]+)"/.exec(headers)?.[1];
        return [{ name, filename, value: filename ? null : body.toString('utf8'), bytes: body.length }];
      });
      state.edits.push(entries); pendingEdit = res; return;
    }
    if (route.startsWith('/outputs/')) { res.writeHead(200, { 'Content-Type': 'image/png' }); return res.end(png); }
    const asset = pathname.replace(/^\/workshop\/imagen\/tool(?=\/)/, '');
    const target = asset.startsWith('/assets/') ? path.join(dist, asset) : path.join(dist, 'index.html');
    const contentType = target.endsWith('.js') ? 'application/javascript' : target.endsWith('.css') ? 'text/css' : 'text/html';
    res.writeHead(200, { 'Content-Type': contentType }); res.end(fs.readFileSync(target));
  } catch (error) { respond(res, { message: error.message }, 500); }
});

let edge, ws;
const checks = [];
try {
  assert.ok(fs.existsSync(path.join(dist, 'index.html')), 'Run npm run build first');
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  fs.mkdirSync(path.join(root, '.run'), { recursive: true });
  const profile = fs.mkdtempSync(path.join(root, '.run/parameter-ui-browser-'));
  const binary = process.env.IMAGEN_BROWSER_BINARY || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  assert.ok(fs.existsSync(binary), 'Set IMAGEN_BROWSER_BINARY to a Chromium/Edge executable');
  edge = spawn(binary, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  const portFile = path.join(profile, 'DevToolsActivePort');
  for (let i = 0; i < 150 && !fs.existsSync(portFile); i++) await delay(100);
  assert.ok(fs.existsSync(portFile), 'Browser did not start');
  const port = Number(fs.readFileSync(portFile, 'utf8').split('\n')[0]);
  const targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  ws = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); });
  let id = 0; const pending = new Map(), exceptions = [];
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    const item = pending.get(message.id); if (!item) return;
    pending.delete(message.id); clearTimeout(item.timer);
    message.error ? item.reject(new Error(JSON.stringify(message.error))) : item.resolve(message.result);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => { pending.delete(requestId); reject(new Error(`CDP timeout: ${method}`)); }, 12000);
    pending.set(requestId, { resolve, reject, timer }); ws.send(JSON.stringify({ id: requestId, method, params }));
  });
  const evaluate = async expression => {
    const source = /\bawait\b|;/.test(expression) ? `(async () => { ${expression} })()` : expression;
    const result = await send('Runtime.evaluate', { expression: source, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    await delay(50); // Allow Vue rendering and browser focus/scroll events to settle between actions.
    return result.result.value;
  };
  async function until(expression) {
    for (let i = 0; i < 100; i++) { if (await evaluate(expression)) return; await delay(100); }
    throw new Error(`Condition not met: ${expression}`);
  }
  async function check(name, expression) {
    const result = await evaluate(expression);
    if (result !== true) console.error(await evaluate('JSON.stringify({mode:store()?.mode,drafts:store()?.drafts,viewport:{innerWidth,scrollWidth:document.documentElement.scrollWidth,scale:visualViewport.scale}})'));
    if (result !== true && name.startsWith('Mobile')) console.error(await evaluate('JSON.stringify([...document.querySelectorAll("body *")].map(el => ({tag:el.tagName,class:el.className,right:Math.round(el.getBoundingClientRect().right),width:Math.round(el.getBoundingClientRect().width),minWidth:getComputedStyle(el).minWidth,position:getComputedStyle(el).position,display:getComputedStyle(el).display,text:el.children.length ? "" : el.textContent.slice(0,60)})).filter(el => el.right > 390 && el.width > 0).sort((a,b) => b.width-a.width).slice(0,40))'));
    assert.equal(result, true, name); checks.push(name);
  }
  const browserHelpers = `
    window.store = () => document.querySelector('#app').__vue_app__?.config.globalProperties.$pinia._s.get('image');
    window.field = label => { const el = [...document.querySelectorAll('label')].find(el => el.textContent.trim() === label); return el?.control || el?.querySelector('input,textarea'); };
    window.write = async (label, value) => { await Promise.resolve(); const el = field(label); if (!el) throw Error('Missing field: ' + label); el.focus(); el.value = value; el.dispatchEvent(new Event('input', {bubbles:true})); await Promise.resolve(); el.blur(); };
    window.button = text => [...document.querySelectorAll('button')].find(el => el.textContent.trim() === text);
    window.key = (el, key, options = {}) => el.dispatchEvent(new KeyboardEvent('keydown', {key,bubbles:true,cancelable:true,...options}));
    window.expand = async () => { document.querySelectorAll('.parameter-section').forEach(el => el.open = true); await new Promise(resolve => setTimeout(resolve, 0)); };
    window.imageFile = async (name, mask = false) => { const canvas = document.createElement('canvas'); canvas.width = 24; canvas.height = 16; if (!mask) { const ctx = canvas.getContext('2d'); ctx.fillStyle = '#85ad9d'; ctx.fillRect(0,0,24,16); } return new File([await new Promise(resolve => canvas.toBlob(resolve))],name,{type:'image/png'}); };
    window.upload = async (selector, name, mask = false) => { const el = document.querySelector(selector), dt = new DataTransfer(); dt.items.add(await imageFile(name,mask)); el.files = dt.files; el.dispatchEvent(new Event('change',{bubbles:true})); };
  `;
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setFocusEmulationEnabled', { enabled: true });
  await send('Page.addScriptToEvaluateOnNewDocument', { source: browserHelpers });
  await send('Emulation.setDeviceMetricsOverride', { width: 1480, height: 1020, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: `${base}/` });
  await until('Boolean(store()?.config && store().images.length && document.querySelector(".mode-form"))');

  await evaluate('await expand(); await write("提示词", "中文测试：一只陶瓷杯");');
  await check('Every dropdown accepts text', 'document.querySelectorAll("select").length === 0 && [...document.querySelectorAll("[role=combobox]")].every(el => el.tagName === "INPUT" && !el.readOnly)');
  await evaluate('await write("模型", "custom-image-model"); await write("尺寸", "1536x864"); await write("质量", "custom-quality"); await write("格式", "webp"); await write("背景", "transparent"); await write("审查设置", "custom-policy"); await write("风格", "custom-style"); await write("响应形式", "custom-response"); await write("输出压缩参数", "0"); await write("请求超时（秒）", "12.5"); await write("扩展参数 JSON", \'{"seed":0,"watermark":false}\');');
  await check('Custom values stay in draft', 'store().drafts.generate.options.model === "custom-image-model" && store().drafts.generate.options.quality === "custom-quality" && field("模型").value === "custom-image-model"');
  await evaluate('await write("数量", "3")');
  await check('Count overflow is visible without clamping', 'field("数量").value === "3" && field("数量").getAttribute("aria-invalid") === "true" && button("生成图片").disabled');
  await evaluate('await write("数量", "1"); await write("格式", "gif")');
  await check('Unsupported local format stays editable with error', 'field("格式").value === "gif" && field("格式").getAttribute("aria-invalid") === "true"');
  await evaluate('await write("格式", "jpeg")');
  await check('JPEG transparency conflict is visible', 'field("背景").getAttribute("aria-invalid") === "true"');
  await evaluate('await write("格式", "webp"); await write("扩展参数 JSON", \'{"model":"override"}\')');
  await check('Extensions cannot replace controls', 'field("扩展参数 JSON").getAttribute("aria-invalid") === "true" && button("生成图片").disabled');
  await evaluate('await write("扩展参数 JSON", \'{"seed":0,"watermark":false}\'); document.querySelector("[aria-label=交换宽高]").click();');
  await check('Width and height swap uses the same size', 'field("尺寸").value === "864x1536" && field("宽").value === "864" && field("高").value === "1536"');
  await evaluate('await write("尺寸", "1536x864"); await write("质量", "low"); field("质量").focus(); key(field("质量"), "ArrowUp"); key(field("质量"), "Enter");');
  await check('First ArrowUp selects the last suggestion', 'field("质量").value === "high"');
  await evaluate('await write("质量", "custom-quality"); field("模型").focus(); key(field("模型"), "Enter", {isComposing:true});');
  assert.equal(state.submissions.length, 0, 'IME Enter must not submit'); checks.push('IME Enter does not submit');
  await evaluate('document.querySelector("[aria-label=展开模型建议]").click()');
  await check('Custom value has a selectable option', '[...document.querySelectorAll("[role=option]")].some(el => el.textContent.includes("custom-image-model"))');
  await evaluate('const form = document.querySelector(".mode-form"); form.scrollTop += 90;');
  await until('field("模型").getAttribute("aria-expanded") === "false"'); checks.push('Suggestions close on parent scroll');
  await evaluate('await write("参数预设", "我的自定义参数"); button("保存预设").click()');
  await check('Named preset preserves custom parameters', 'store().presets.some(item => item.name === "我的自定义参数" && item.options.model === "custom-image-model")');
  await evaluate('await write("模型", "second-model"); await write("参数预设", "未保存名称")');
  await check('Typing an unknown preset leaves parameters alone', 'field("模型").value === "second-model"');
  await evaluate('await write("参数预设", "我的自定义参数"); button("应用").click()');
  await check('Preset application preserves prompt', 'field("模型").value === "custom-image-model" && field("提示词").value === "中文测试：一只陶瓷杯"');
  await evaluate('button("撤销").click()');
  await check('Undo restores prior parameters', 'field("模型").value === "second-model"');
  await evaluate('button("应用").click(); await write("格式", "png")');
  await check('PNG leaves compression draft but omits effective parameter', 'field("输出压缩参数").value === "0" && !("output_compression" in JSON.parse(document.querySelector(".request-preview pre").textContent))');
  await evaluate('await write("格式", "webp"); document.querySelectorAll("[role=tab]")[1].click()');
  await evaluate('await expand(); await write("编辑指令", "独立编辑草稿"); await write("模型", "edit-custom-model"); document.querySelectorAll("[role=tab]")[0].click()');
  await check('Mode switches retain independent drafts', 'field("模型").value === "custom-image-model" && store().drafts.edit.prompt === "独立编辑草稿"');
  await send('Page.reload'); await until('Boolean(store()?.config && store().images.length)');
  await check('Reload restores custom drafts and presets', 'store().drafts.generate.options.model === "custom-image-model" && store().drafts.edit.options.model === "edit-custom-model" && store().presets.some(item => item.name === "我的自定义参数")');
  await evaluate('button("生成图片").click()'); await until('store().isBusy && Boolean(store().activeJob)');
  assert.equal(state.submissions[0].options.output_compression, 0);
  assert.deepEqual(state.submissions[0].options.extra_body, { seed: 0, watermark: false });
  assert.equal(state.submissions[0].options.style, 'custom-style'); checks.push('Generation POST sends complete custom options');
  await evaluate('await write("模型", "next-draft-model")');
  await check('Editing while busy leaves submitted snapshot intact', 'store().activeJob.options.model === "custom-image-model" && field("模型").value === "next-draft-model" && !field("模型").disabled');
  Object.assign(state.jobs[0], { status: 'failed', error: 'Synthetic quality rejection', error_fields: { quality: 'Synthetic quality rejection' } });
  await until('!store().isBusy');
  await check('Old task errors do not label a changed draft', 'Object.keys(store().fieldErrors.generate).length === 0 && field("模型").value === "next-draft-model"');
  await evaluate('button("载入设置后重试").click()');
  await check('Failed settings load for a manual retry', 'field("模型").value === "custom-image-model" && !store().isBusy');
  await evaluate('key(field("提示词"), "Enter", {ctrlKey:true})'); await until('store().isBusy && store().activeJob?.id === "job-2"');
  checks.push('Ctrl+Enter submits a valid draft');
  Object.assign(state.jobs[0], { status: 'failed', error: 'Synthetic quality rejection', error_fields: { quality: 'Synthetic quality rejection' } });
  await until('!store().isBusy');
  await check('An unchanged failed draft receives field errors', 'store().fieldErrors.generate.quality === "Synthetic quality rejection" && field("质量").getAttribute("aria-invalid") === "true"');
  await evaluate('button("载入设置后重试").click(); await write("质量", "high"); button("生成图片").click()');
  await until('store().isBusy && store().activeJob?.id === "job-3"');
  const modern = { ...oldImage, id: 'modern-1', prompt: state.jobs[0].prompt, model: state.jobs[0].options.model,
    quality: 'high', size: '1536x864', created_at: new Date().toISOString(), options: state.jobs[0].options };
  state.images.unshift(modern); Object.assign(state.jobs[0], { status: 'succeeded', images: [modern] });
  await until('!store().isBusy && store().selectedImageId === "modern-1"');
  await evaluate('await write("模型", "changed-model"); document.querySelector("[aria-label=复用完整设置]").click()');
  await check('Full history reuse restores all options', 'store().drafts.generate.options.model === "custom-image-model" && store().drafts.generate.options.style === "custom-style" && store().drafts.generate.options.timeout === "12.5"');

  await evaluate('document.querySelectorAll("[role=tab]")[1].click()');
  await evaluate('await upload("input[multiple]", "first.png"); await upload("input[multiple]", "second.png"); await upload("input[accept=\\"image/png\\"]", "mask.png", true);');
  await until('store().editInputs.length === 2 && Boolean(store().editMask)');
  await check('Uploads enter input list and mask shows dimensions', 'store().editInputs[0].filename === "first.png" && store().editMask.width === 24 && Boolean(document.querySelector(".mask-preview"))');
  await evaluate('document.querySelectorAll(".queue-item [title=上移]")[1].click()');
  await check('Reordering changes actual input order', 'store().editInputs[0].filename === "second.png"');
  await evaluate('await expand(); await write("尺寸", "1536x864"); await write("质量", "custom-edit-quality"); await write("格式", "webp"); await write("背景", "transparent"); await write("输入图保真度", "custom-fidelity"); await write("输出压缩参数", "0"); await write("审查设置", "low"); await write("请求超时（秒）", "5"); await write("响应形式", "b64_json"); await write("扩展参数 JSON", \'{"seed":0,"watermark":false}\'); button("编辑图片").click()');
  await until('store().isEditing && Boolean(store().pendingEdit)');
  for (let i = 0; i < 100 && !pendingEdit; i++) await delay(20);
  const entries = state.edits[0], form = Object.fromEntries(entries.filter(entry => !entry.filename).map(entry => [entry.name, entry.value]));
  assert.equal(form.input_fidelity, 'custom-fidelity'); assert.equal(form.output_compression, '0');
  assert.deepEqual(JSON.parse(form.extra_body), { seed: 0, watermark: false });
  assert.ok(!('style' in form));
  assert.deepEqual(entries.filter(entry => entry.name === 'images').map(entry => entry.filename), ['second.png', 'first.png']);
  assert.equal(entries.find(entry => entry.name === 'mask').filename, 'mask.png'); checks.push('Edit multipart sends options, mask, and ordered files');
  await evaluate('await write("模型", "next-edit-model"); document.querySelector(".queue-item [title=移除]").click()');
  await check('Edit snapshot is immutable while next draft changes', 'store().pendingEdit.options.model === "edit-custom-model" && store().editInputs.length === 1 && field("模型").value === "next-edit-model"');
  respond(pendingEdit, { detail: { message: 'Synthetic mask rejection', code: 'invalid_mask', fields: { mask: 'Synthetic mask rejection' } } }, 400); pendingEdit = null;
  await until('!store().isEditing');
  await check('Edit errors do not label changed inputs', 'Object.keys(store().fieldErrors.edit).length === 0');
  await evaluate('store().clearError(); button("编辑图片").click()'); await until('store().isEditing');
  for (let i = 0; i < 100 && !pendingEdit; i++) await delay(20);
  respond(pendingEdit, { detail: { message: 'Synthetic mask rejection', code: 'invalid_mask', fields: { mask: 'Synthetic mask rejection' } } }, 400); pendingEdit = null;
  await until('!store().isEditing');
  await check('Unchanged edit shows mask error and retains mask', 'store().fieldErrors.edit.mask === "Synthetic mask rejection" && store().editMask.filename === "mask.png"');
  await send('Page.reload'); await until('Boolean(store()?.config && store().images.length)');
  await check('Reload identifies upload files that must be reselected', 'store().mode === "edit" && store().missingUploadNames.includes("first.png") && store().missingUploadNames.includes("mask.png") && store().uploadedAssets.length === 0 && Boolean(document.querySelector(".missing-assets"))');

  await evaluate('button("忽略缺失素材").click(); document.querySelectorAll("[role=tab]")[0].click(); store().notice = null; await expand(); document.querySelector(".mode-form").scrollTop = 0;');
  await check('Desktop layout has no horizontal overflow', 'document.documentElement.scrollWidth <= innerWidth');
  fs.writeFileSync(path.join(root, '.run/parameter-workspace-live-desktop.png'), Buffer.from((await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })).data, 'base64'));
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 1040, screenWidth: 390, screenHeight: 1040, deviceScaleFactor: 1, mobile: true });
  await send('Page.reload'); await until('Boolean(store()?.config && store().images.length)');
  await check('Mobile layout has no horizontal overflow', 'innerWidth === 390 && document.documentElement.scrollWidth <= innerWidth');
  await check('Mobile header leaves room for mode tabs', 'document.querySelector(".mode-switch").getBoundingClientRect().bottom <= document.querySelector(".preset-controls").getBoundingClientRect().top');
  fs.writeFileSync(path.join(root, '.run/parameter-workspace-live-mobile.png'), Buffer.from((await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })).data, 'base64'));

  await send('Page.navigate', { url: `${base}/workshop/imagen/tool/` });
  await until('Boolean(store()?.config && store().images.length)');
  await check('Embedded route retains existing media-library integration', 'Boolean(document.querySelector("[aria-label=发布到站点媒体库]")) && store().drafts.generate.options.model === ""');
  assert.ok(state.apiPaths.includes('/workshop/imagen/api/config')); checks.push('Embedded API paths stay under the same-origin BFF');
  assert.deepEqual(exceptions, []);
  console.log(JSON.stringify({ passed: checks.length, checks, screenshots: ['.run/parameter-workspace-live-desktop.png', '.run/parameter-workspace-live-mobile.png'] }, null, 2));
} catch (error) {
  console.error(JSON.stringify({ passed: checks.length, checks, failure: error.stack }, null, 2)); process.exitCode = 1;
} finally {
  if (ws?.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ id: 999999, method: 'Browser.close' })); await delay(300); ws.close(); }
  if (edge && edge.exitCode === null) edge.kill();
  if (pendingEdit) pendingEdit.end();
  server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
}
