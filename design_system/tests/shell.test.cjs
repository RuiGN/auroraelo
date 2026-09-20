const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../static/design_system/js/shell.js'), 'utf8');

// Synthetic DOM contract: no clinical payloads, network or real user data.
function boot(matches) {
  const toggle = {
    listeners: {}, attrs: {}, focused: false,
    addEventListener(type, callback) { this.listeners[type] = callback; },
    setAttribute(key, value) { this.attrs[key] = value; },
    focus() { this.focused = true; },
  };
  const navigation = { hidden: false };
  const buttons = ['vertical', 'horizontal'].map((mode) => ({
    dataset: { auroraLayout: mode }, attrs: {},
    addEventListener(type, callback) { this.click = callback; },
    setAttribute(key, value) { this.attrs[key] = value; },
  }));
  const portal = {
    dataset: { layout: 'vertical' }, listeners: {},
    querySelector() { return toggle; },
    querySelectorAll() { return buttons; },
    addEventListener(type, callback) { this.listeners[type] = callback; },
  };
  const media = {
    matches,
    addEventListener(type, callback) { this.change = callback; },
  };
  runInNewContext(source, {
    document: {
      addEventListener(type, callback) { callback(); },
      querySelector() { return portal; },
      getElementById() { return navigation; },
    },
    window: { matchMedia() { return media; } },
  });
  return { toggle, navigation, buttons, portal, media };
}

test('mobile disclosure and Escape keep aria state and keyboard focus', () => {
  const { toggle, navigation, portal } = boot(true);
  assert.equal(navigation.hidden, true);
  assert.equal(toggle.attrs['aria-expanded'], 'false');
  toggle.listeners.click();
  assert.equal(navigation.hidden, false);
  assert.equal(toggle.attrs['aria-expanded'], 'true');
  portal.listeners.keydown({ key: 'Escape' });
  assert.equal(navigation.hidden, true);
  assert.equal(toggle.focused, true);
});

test('desktop navigation and layout switch remain usable after resize', () => {
  const { media, navigation, portal, buttons } = boot(false);
  assert.equal(navigation.hidden, false);
  buttons[1].click();
  assert.equal(portal.dataset.layout, 'horizontal');
  assert.equal(buttons[1].attrs['aria-pressed'], 'true');
  assert.equal(buttons[0].attrs['aria-pressed'], 'false');
  media.matches = true;
  media.change();
  assert.equal(navigation.hidden, true);
  media.matches = false;
  media.change();
  assert.equal(navigation.hidden, false);
});
