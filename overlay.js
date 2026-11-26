/* agy-cn: 运行时界面汉化层。只替换界面文字，不修改任何应用文件，不发起网络请求。 */
(function (dict) {
  'use strict';
  if (typeof document === 'undefined' || window.__agyCnInstalled) return;
  window.__agyCnInstalled = true;

  const map = new Map();
  for (const [k, v] of Object.entries(dict.phrases || {})) {
    map.set(k, v);
    map.set(k.toLowerCase(), v);
  }
  const ATTRS = ['title', 'aria-label', 'placeholder'];
  // 这些区域内绝不翻译：输入框、代码、编辑器、对话内容（Markdown 渲染区）
  const SKIP = 'textarea,input,pre,code,script,style,[contenteditable="true"],.monaco-editor,.markdown,.prose,[class*="markdown"],[class*="message-content"],[data-agycn-skip="1"]';

  const U = { s: '秒', m: '分钟', h: '小时', d: '天', w: '周', mo: '个月', y: '年' };
  const UL = { second: 's', minute: 'm', hour: 'h', day: 'd', week: 'w', month: 'mo', year: 'y' };
  function dur(x) {
    // "20s" / "1m 5s" / "3 minutes" → 中文
    const parts = x.trim().replace(/,?\s+and\s+/g, ' ').split(/,?\s+(?=\d)/);
    const out = [];
    for (const p of parts) {
      const m = p.match(/^(\d+)\s*(mo|s|m|h|d|w|y|second|minute|hour|day|week|month|year)s?$/i);
      if (!m) return undefined;
      const u = m[2].toLowerCase();
      out.push(m[1] + ' ' + U[UL[u] || u]);
    }
    return out.join(' ');
  }
  const RULES = [
    [/^(just now|now)$/i, () => '刚刚'],
    [/^(.+?)\s+ago$/i, (m) => { const d = dur(m[1]); return d && d + '前'; }],
    [/^(\d+)\s*(mo|s|m|h|d|w|y)$/, (m) => m[1] + ' ' + U[m[2]]],
    [/^(\d+) files? changed$/i, (m) => '已更改 ' + m[1] + ' 个文件'],
    [/^Worked for (.+)$/i, (m) => { const d = dur(m[1]); return d && '已工作 ' + d; }],
    [/^Show (\d+) breakdowns?$/i, (m) => '显示 ' + m[1] + ' 项明细'],
    [/^\(([\d,]+) tokens\)$/i, (m) => '(' + m[1] + ' tokens)'],
    [/^You have used some of your (weekly|5-hour) limit, it will fully refresh in (.+)\.$/i,
      (m) => { const d = dur(m[2]); return d && '你已使用部分' + (m[1].toLowerCase() === 'weekly' ? '本周' : '5 小时') + '额度，将在 ' + d + '后完全恢复。'; }],
    [/^Thought for (.+)$/i, (m) => { const d = dur(m[1]); return d && '已思考 ' + d; }],
    [/^Thinking for (.+)$/i, (m) => { const d = dur(m[1]); return d && '正在思考 ' + d; }],
    [/^Your plan's baseline quota will refresh on (.+?)\. To continue using this model now, enable AI Credit overages\.$/i,
      (m) => '你的套餐基础配额将在 ' + m[1] + ' 刷新。如需立即继续使用此模型，请开启 AI 积分超额抵扣。'],
    [/^Turn (\d+) of (\d+)$/i, (m) => '第 ' + m[1] + ' / ' + m[2] + ' 轮'],
    [/^Load older messages, showing (\d+) of (\d+)$/i, (m) => '加载更早消息（已显示 ' + m[1] + ' / ' + m[2] + ' 条）'],
    [/^No more older messages, showing (\d+) of (\d+)$/i, (m) => '没有更早的消息（已显示 ' + m[1] + ' / ' + m[2] + ' 条）'],
    [/^Add shortcut for (.+)$/i, (m) => '为「' + (map.get(m[1]) || m[1]) + '」添加快捷键'],
    [/^Remove shortcut (.+?) for (.+)$/i, (m) => '移除「' + (map.get(m[2]) || m[2]) + '」的快捷键 ' + m[1]],
    [/^Shortcut (.+?) for (.+)$/i, (m) => '「' + (map.get(m[2]) || m[2]) + '」的快捷键 ' + m[1]],
    [/^Your plan: (.+)$/i, (m) => '当前套餐：' + m[1]],
    [/^Updated (.+)$/i, (m) => '更新于 ' + m[1]],
    [/^Select model, current: (.+)$/i, (m) => '选择模型，当前：' + m[1]],
    [/^Select project, current: (.+)$/i, (m) => '选择项目，当前：' + m[1]],
    [/^Where the agent runs, current: (.+)$/i, (m) => '智能体运行位置，当前：' + m[1]],
    [/^Agent permissions preset selector, current: (.+)$/i, (m) => '智能体权限预设，当前：' + m[1]],
    [/^Skills: ([\d,]+) tokens$/i, (m) => '技能：' + m[1] + ' tokens'],
  ];
  const missing = window.__agyCnMissing = new Set();
  function lookup(s) {
    const t = s.trim();
    if (!t || t.length > 400) return undefined;
    // 全小写的词（如技能名 conversations）不做忽略大小写匹配，避免误翻
    const ident = /^[a-z0-9_-]+$/.test(t);  // 像标识符（技能名、命令名）的全小写词不查词典
    let r = ident ? undefined : (map.get(t) ?? map.get(t.toLowerCase()));
    if (r !== undefined) return r;
    for (const [re, fn] of RULES) {
      const m = t.match(re);
      if (m) { r = fn(m); if (r) return r; }
    }
    // 记录未翻译的英文短语，供补充词典
    if (/^[A-Za-z][A-Za-z0-9 .,'&()/:+-]{1,60}$/.test(t) && missing.size < 2000) missing.add(t);
    return undefined;
  }
  function skipped(el) {
    return !el || (el.closest && el.closest(SKIP));
  }
  // 双语模式：短标签（菜单、标题、按钮）显示「中文 English」；长句只显示中文
  const BILINGUAL = true;
  function label(src, zh) {
    const t = src.trim();
    if (!BILINGUAL || t.length > 32 || /[.?!:]$/.test(t) || /\d/.test(t) || zh === t) return zh;
    return zh + ' ' + t;
  }
  // 设置侧栏里的分组标题：做成不可点的小号灰色标题，避免误点
  const HEADINGS = new Set(['Settings', 'Projects', 'Not in Project']);
  function styleHeading(node) {
    const el = node.parentElement;
    if (!el || !HEADINGS.has(node.nodeValue.trim())) return;
    if (el.closest('button,a,[role="button"],[role="menuitem"],[role="tab"]')) return; // 真按钮不动
    if (!el.closest('[role="dialog"],[class*="modal"],[class*="dialog"]')) return;     // 只作用于设置弹窗
    el.classList.add('agycn-heading');
  }
  if (!document.getElementById('agycn-style')) {
    const st = document.createElement('style');
    st.id = 'agycn-style';
    st.textContent = '.agycn-heading{font-size:11px!important;font-weight:700!important;letter-spacing:.06em!important;' +
      'color:#9aa0a6!important;cursor:default!important;pointer-events:none!important;user-select:none!important;' +
      'margin-top:10px!important;padding-bottom:2px!important;border-bottom:1px solid rgba(128,128,128,.25)!important}' +
      '#agycn-bg-layer{position:fixed;top:0;right:0;bottom:0;left:0;pointer-events:none;z-index:2147483600;' +
      'background-position:center;background-size:cover;background-repeat:no-repeat;transition:opacity .2s,left .2s}' +
      '#agycn-bg-card{width:100%;box-sizing:border-box;margin:16px 0;padding:14px 16px;border-radius:12px;border:1px solid rgba(128,128,128,.22);' +
      'background:rgba(128,128,128,.05);font-size:13px;line-height:1.5}' +
      '#agycn-bg-card .agycn-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:10px;flex-wrap:wrap}' +
      '#agycn-bg-card button{padding:5px 12px;border-radius:8px;border:1px solid rgba(128,128,128,.3);background:transparent;' +
      'color:inherit;cursor:pointer;font-size:12px}#agycn-bg-card button:hover{background:rgba(128,128,128,.12)}' +
      '#agycn-bg-card button.primary{background:#2f75c3;color:#fff;border-color:#2f75c3}' +
      '#agycn-bg-card input[type=range]{width:140px;vertical-align:middle}';
    (document.head || document.documentElement).appendChild(st);
  }

  // 自定义背景图（本地保存，不联网）
  const isMainApp = typeof location !== 'undefined' && /^https?:\/\/127\.0\.0\.1/.test(location.href);
  let bgCfg = Object.assign({ dataUrl: '', opacity: 0.18, blur: 0, scope: 'all' }, dict.bg || {});

  function isDarkBg() {
    try {
      const m = getComputedStyle(document.body).backgroundColor.match(/\d+/g);
      if (!m || m.length < 3) return false;
      return (0.299 * +m[0] + 0.587 * +m[1] + 0.114 * +m[2]) < 128;
    } catch (_) { return false; }
  }
  function findSidebarWidth() {
    const aside = document.querySelector('aside, nav, [class*="sidebar"]');
    if (aside) {
      const r = aside.getBoundingClientRect();
      if (r.left <= 10 && r.width >= 140 && r.width <= 460) return Math.round(r.right);
    }
    return 260;
  }
  function applyBg() {
    if (!isMainApp || !document.body) return;
    let el = document.getElementById('agycn-bg-layer');
    if (!bgCfg.dataUrl) {
      if (el) el.remove();
      return;
    }
    if (!el) {
      el = document.createElement('div');
      el.id = 'agycn-bg-layer';
      document.body.appendChild(el);
    }
    el.style.backgroundImage = 'url("' + bgCfg.dataUrl + '")';
    el.style.opacity = String(bgCfg.opacity);
    el.style.filter = bgCfg.blur ? 'blur(' + bgCfg.blur + 'px)' : 'none';
    el.style.mixBlendMode = isDarkBg() ? 'screen' : 'multiply';
    el.style.left = bgCfg.scope === 'chat' ? findSidebarWidth() + 'px' : '0px';
  }
  function persistBg() {
    applyBg();
    try {
      if (typeof window.__agyCnSaveBg === 'function') window.__agyCnSaveBg(JSON.stringify(bgCfg));
    } catch (_) {}
  }
  function compressImage(file, cb) {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const max = 1920;
        let w = img.width, h = img.height;
        if (w > max || h > max) {
          const s = Math.min(max / w, max / h);
          w = Math.round(w * s); h = Math.round(h * s);
        }
        const c = document.createElement('canvas');
        c.width = w; c.height = h;
        c.getContext('2d').drawImage(img, 0, 0, w, h);
        cb(c.toDataURL('image/jpeg', 0.82));
      };
      img.onerror = () => cb(reader.result);
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  }
  function mountBgCard() {
    if (!isMainApp || document.getElementById('agycn-bg-card')) return;
    const dlg = document.querySelector('[role="dialog"],[class*="modal"],[class*="dialog"]');
    if (!dlg) return;
    // 只在「外观 Appearance」设置页里挂载
    const txt = dlg.innerText || '';
    if (!/Dark Theme|深色主题/.test(txt) || !/Light Theme|浅色主题/.test(txt)) return;
    const anchor = Array.from(dlg.querySelectorAll('h1,h2,h3,div,span'))
      .find(e => e.childElementCount === 0 && /^(深色主题 Dark Theme|Dark Theme|深色主题)$/.test((e.textContent || '').trim()));
    if (!anchor || !anchor.parentElement) return;
    const card = document.createElement('div');
    card.id = 'agycn-bg-card';
    card.setAttribute('data-agycn-skip', '1');
    card.innerHTML =
      '<div style="font-weight:600">自定义背景图 Custom Background</div>' +
      '<div style="opacity:.7;font-size:12px;margin-top:2px">仅保存在本地 ~/.agy-cn/，不联网，选择图片后立即生效。</div>' +
      '<div class="agycn-row">' +
        '<div><button type="button" class="primary" id="agycn-bg-pick">上传图片 Upload</button> ' +
        '<button type="button" id="agycn-bg-clear">清除 Clear</button>' +
        '<input type="file" id="agycn-bg-file" accept="image/*" style="display:none"></div>' +
        '<div>范围：<button type="button" id="agycn-bg-scope">' + (bgCfg.scope === 'chat' ? '仅对话区' : '整个窗口') + '</button></div>' +
      '</div>' +
      '<div class="agycn-row">' +
        '<label>透明度 <input type="range" id="agycn-bg-op" min="5" max="60" value="' + Math.round(bgCfg.opacity * 100) + '"> ' +
        '<span id="agycn-bg-opv">' + Math.round(bgCfg.opacity * 100) + '%</span></label>' +
        '<label>模糊 <input type="range" id="agycn-bg-bl" min="0" max="12" value="' + bgCfg.blur + '"> ' +
        '<span id="agycn-bg-blv">' + bgCfg.blur + 'px</span></label>' +
      '</div>';
    // 向上找到纵向排版容器的直接子块，确保独立占满一行，不和标题挤在同一行
    let host = anchor;
    while (host.parentElement && host.parentElement !== dlg) {
      const cs = getComputedStyle(host.parentElement);
      const isVert = cs.display === 'block' || (cs.display.includes('flex') && cs.flexDirection === 'column');
      if (isVert && host.parentElement.children.length >= 2 && host.getBoundingClientRect().width > 300) break;
      host = host.parentElement;
    }
    host.parentElement.insertBefore(card, host);
    const fileInput = card.querySelector('#agycn-bg-file');
    card.querySelector('#agycn-bg-pick').onclick = () => fileInput.click();
    fileInput.onchange = () => {
      const f = fileInput.files && fileInput.files[0];
      if (!f) return;
      compressImage(f, (dataUrl) => { bgCfg.dataUrl = dataUrl; persistBg(); });
      fileInput.value = '';
    };
    card.querySelector('#agycn-bg-clear').onclick = () => { bgCfg.dataUrl = ''; persistBg(); };
    const scopeBtn = card.querySelector('#agycn-bg-scope');
    scopeBtn.onclick = () => {
      bgCfg.scope = bgCfg.scope === 'chat' ? 'all' : 'chat';
      scopeBtn.textContent = bgCfg.scope === 'chat' ? '仅对话区' : '整个窗口';
      persistBg();
    };
    const op = card.querySelector('#agycn-bg-op'), opv = card.querySelector('#agycn-bg-opv');
    op.oninput = () => { bgCfg.opacity = Number(op.value) / 100; opv.textContent = op.value + '%'; applyBg(); };
    op.onchange = persistBg;
    const bl = card.querySelector('#agycn-bg-bl'), blv = card.querySelector('#agycn-bg-blv');
    bl.oninput = () => { bgCfg.blur = Number(bl.value); blv.textContent = bl.value + 'px'; applyBg(); };
    bl.onchange = persistBg;
  }
  function doText(node) {
    if (skipped(node.parentElement)) return;
    styleHeading(node);
    let r = lookup(node.nodeValue);
    if (r !== undefined) r = label(node.nodeValue, r);
    if (r !== undefined) {
      const lead = node.nodeValue.match(/^\s*/)[0], tail = node.nodeValue.match(/\s*$/)[0];
      node.nodeValue = lead + r + tail;
    }
  }
  function doEl(el) {
    if (skipped(el)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (v) { const r = lookup(v); if (r !== undefined) el.setAttribute(a, r); }
    }
  }
  function walk(root) {
    if (root.nodeType === 3) return doText(root);
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) doEl(root);
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    let n;
    while ((n = w.nextNode())) n.nodeType === 3 ? doText(n) : doEl(n);
  }
  function start() {
    walk(document.body);
    applyBg();
    mountBgCard();
    let bgTimer = null;
    new MutationObserver(muts => {
      for (const m of muts) {
        if (m.type === 'characterData') doText(m.target);
        else if (m.type === 'attributes') doEl(m.target);
        else m.addedNodes.forEach(walk);
      }
      if (!bgTimer) bgTimer = setTimeout(() => { bgTimer = null; mountBgCard(); applyBg(); }, 200);
    }).observe(document.body, { childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ATTRS });
  }
  if (document.body) start();
  else document.addEventListener('DOMContentLoaded', start, { once: true });
})(/*__DICT__*/);
