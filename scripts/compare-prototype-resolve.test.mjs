import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test } from 'node:test'
import {
  buildAssignmentRoute,
  buildLessonRoute,
  buildQuizRoute,
  buildVerifyRoute,
  credentialIdFromSeedDocument,
  pickFirstAssignmentId,
  pickFirstLessonId,
  pickFirstQuizModuleId,
  readRs16SeedDocument,
} from './compare-prototype-resolve.mjs'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

test('credentialIdFromSeedDocument matches RS-16 Research Methodology certificate', () => {
  const doc = readRs16SeedDocument(repoRoot)
  const id = credentialIdFromSeedDocument(doc, { year: 2026 })
  assert.equal(id, 'RS-16A001-2026-F00DCAFE01')
  assert.equal(buildVerifyRoute(id), '/verify/RS-16A001-2026-F00DCAFE01')
})

test('route builders encode path segments', () => {
  assert.equal(buildLessonRoute('c1', 'l1'), '/courses/c1/lessons/l1')
  assert.equal(buildQuizRoute('c1', 'm1'), '/courses/c1/modules/m1/quiz')
  assert.equal(buildAssignmentRoute('c1', 'a1'), '/courses/c1/assignments/a1')
})

test('pickFirstLessonId chooses lowest moduleOrder then order', () => {
  const id = pickFirstLessonId([
    { id: 'b', moduleOrder: 1, order: 0 },
    { id: 'a', moduleOrder: 0, order: 5 },
  ])
  assert.equal(id, 'a')
})

test('pickFirstQuizModuleId chooses first ordered module with moduleQuiz', () => {
  const id = pickFirstQuizModuleId([
    { id: 'm2', order: 2 },
    { id: 'm0', order: 0, moduleQuiz: { available: true } },
    { id: 'm1', order: 1, moduleQuiz: { available: false } },
  ])
  assert.equal(id, 'm0')
})

test('pickFirstAssignmentId fails clearly when empty', () => {
  assert.throws(() => pickFirstAssignmentId([]), /no assignments/)
  assert.equal(pickFirstAssignmentId([{ id: 'x1' }]), 'x1')
})
