// Minimal DOM smoke test of the published single-file application and real data.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(import.meta.dirname, '..');
const html = fs.readFileSync(path.join(root, 'frontend/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert(script, 'Inline frontend code missing');

const ids = ['pUse', 'questionType', 'pStage', 'pStructure', 'quickTopics',
  'allTopics', 'allTopicsToggle', 'q', 'searchButton', 'resetSettings',
  'clearSearch', 'chapterList', 'resultSummary', 'error'];
const elements = Object.fromEntries(ids.map(id => [id, {
  value: '', innerHTML: '', textContent: '', hidden: false,
  options: [{ value: '' }], listeners: {},
  addEventListener(name, cb) { this.listeners[name] = cb; },
  scrollIntoView() {},
}]));
let clickListener;
const document = {
  getElementById: id => elements[id],
  addEventListener: (event, cb) => { if (event === 'click') clickListener = cb; },
  querySelector: () => null,
};
const fetch = async url => {
  const file = path.join(root, 'frontend', url.split('?')[0].replace(/^\.\//, ''));
  const actual = file.includes('/frontend/data/') ?
    file.replace('/frontend/data/', '/data/') : file;
  return { ok: fs.existsSync(actual), json: async () => JSON.parse(fs.readFileSync(actual, 'utf8')) };
};

vm.runInNewContext(script, {
  document, fetch, console, setTimeout, clearTimeout, window: {scrollY:0,scrollTo(){}},
  localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
});
await new Promise(resolve => setTimeout(resolve, 100));
assert(elements.chapterList.innerHTML.includes('مبحث ۴'), 'Chapter 4 absent');
assert(elements.chapterList.innerHTML.includes('مبحث ۵'), 'Chapter 5 absent');
assert(elements.quickTopics.innerHTML.includes('عرض راه پله'), 'Quick topic absent');

function clickTopic(label, chapter) {
  clickListener({ target: { closest(selector) {
    if (selector === '[data-topic]') return { dataset: { topic: label, ch: String(chapter) } };
    return null;
  } } });
}
clickTopic('عرض راه پله', 4);
assert(elements.chapterList.innerHTML.includes('hit-list'), 'Focused search layout missing');
assert(elements.chapterList.innerHTML.includes('مبحث ۴'), 'Expected stair-width regulation not ranked');
assert(elements.chapterList.innerHTML.includes('data-lazy="1"'), 'Full text must load only on demand');

// Numeric lookup must locate the exact clause without opening an entire book.
elements.q.value = '4-5-1-7-3';
elements.searchButton.onclick();
assert(elements.chapterList.innerHTML.includes('4-5-1-7-3'), 'Exact clause lookup failed');

// No query shows browsable chapters and defers building their nested hierarchy.
elements.q.value = '';
elements.searchButton.onclick();
assert(elements.chapterList.innerHTML.includes('data-chapter="4"'), 'Chapter browsing missing');
assert(elements.chapterList.innerHTML.includes('class="chapterbody" data-lazy="1"'), 'Hierarchy should load on demand');
console.log('Frontend smoke test passed: ranked lookup, numeric clause, lazy hierarchy.');
