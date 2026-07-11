import assert from 'node:assert/strict';
import test from 'node:test';
import { apiErrorMessage } from './apiError.ts';

test('prefers FastAPI detail', () => {
  assert.equal(apiErrorMessage({ response: { data: { detail: '参数无效' } } }, '失败'), '参数无效');
});

test('falls back through API message and Error message', () => {
  assert.equal(apiErrorMessage({ response: { data: { message: '服务繁忙' } } }, '失败'), '服务繁忙');
  assert.equal(apiErrorMessage(new Error('网络断开'), '失败'), '网络断开');
  assert.equal(apiErrorMessage(null, '失败'), '失败');
});
