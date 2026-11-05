import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { UserConfig } from 'vite';
import config from '../vite.config';

test('Vite uses only backend-allowlisted ports and preserves original Host/Origin checks', () => {
  const vite = config as UserConfig;
  assert.equal(vite.server?.port, 5173);
  assert.equal(vite.preview?.port, 4173);
  for (const target of [vite.server, vite.preview]) {
    assert.equal(target?.strictPort, true);
    const proxy = target?.proxy?.['/api'];
    assert.ok(proxy && typeof proxy === 'object');
    assert.equal(proxy.target, 'http://127.0.0.1:8000');
    assert.equal(proxy.changeOrigin, false);
  }
});
