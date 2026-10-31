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
  'allTopicsToggle', 'tagSummary', 'activeFacets', 'resetFacets',
  'facetChapter', 'facetSection', 'facetSub', 'facetKind',
  'q', 'searchButton', 'resetSettings', 'clearSearch', 'chapterList', 'resultSummary', 'error'];
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
assert(elements.facetChapter.innerHTML.includes('مبحث'), 'Chapter facets missing');

elements.q.value = 'عرض راه پله';
elements.searchButton.onclick();
assert(elements.chapterList.innerHTML.includes('hit-list'), 'Focused search layout missing');
assert(elements.chapterList.innerHTML.includes('مبحث ۴'), 'Expected stair-width regulation not ranked');
assert(elements.chapterList.innerHTML.includes('data-lazy="1"'), 'Full text must load only on demand');
assert(elements.quickTopics.innerHTML.includes('پله'), 'Visible results must determine tags');
elements.facetChapter.value = '4';
elements.facetChapter.listeners.change();
assert(elements.chapterList.innerHTML.includes('مبحث ۴'), 'Chapter facet must preserve matching results');
assert(!elements.chapterList.innerHTML.includes('hit-topic">مبحث ۳'), 'Chapter facet must remove other chapters');
elements.facetKind.value = 'measure';
elements.facetKind.listeners.change();
assert(elements.resultSummary.textContent.includes('بند مطابق'), 'Content type facet must refresh result count');
elements.resetFacets.onclick();
assert(elements.facetChapter.value === '', 'Reset facets must clear selection');

// Numeric lookup must locate the exact clause without opening an entire book.
elements.q.value = '4-5-1-7-3';
elements.searchButton.onclick();
assert(elements.chapterList.innerHTML.includes('4-5-1-7-3'), 'Exact clause lookup failed');

// No query shows browsable chapters and defers building their nested hierarchy.
elements.q.value = '';
elements.searchButton.onclick();
assert(elements.chapterList.innerHTML.includes('data-chapter="4"'), 'Chapter browsing missing');
assert(elements.chapterList.innerHTML.includes('class="chapterbody" data-lazy="1"'), 'Hierarchy should load on demand');
console.log('Frontend smoke test passed: scoped facets, dynamic tags, ranked lookup, numeric clause, lazy hierarchy.');
