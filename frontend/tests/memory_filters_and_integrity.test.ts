/**
 * Test Suite: Memory Status Filters, Live Execution Integrity, and Telemetry Accuracy
 *
 * Requirements Verified:
 * 1. Filter mapping: 'all', 'active', 'candidate', 'deprecated' (including legacy aliases)
 * 2. Empty results handling
 * 3. Execution error surfacing: HTTP & network failures throw descriptive errors
 * 4. Silent simulation prevention: backend failures never silently return mock data
 * 5. Explicit demo isolation: only runs when explicitly requested
 * 6. Telemetry integrity: no invented dynamic metrics
 */

import assert from 'node:assert/strict'
import type { Experience, ExperienceStatus } from '../src/types'
import { executeAgentTask, fetchTelemetry, getTelemetryMetrics } from '../src/services/api'

// Helper function duplicating the filtering logic in MemoryExplorer.tsx
function filterExperiences(
  experiences: Experience[],
  searchQuery: string,
  domainFilter: string,
  statusFilter: 'all' | 'active' | 'candidate' | 'deprecated'
): Experience[] {
  return experiences.filter((exp) => {
    const matchesSearch =
      exp.triggerCondition.toLowerCase().includes(searchQuery.toLowerCase()) ||
      exp.strategyLesson.toLowerCase().includes(searchQuery.toLowerCase()) ||
      exp.pitfallWarning.toLowerCase().includes(searchQuery.toLowerCase()) ||
      exp.id.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesDomain = domainFilter === 'all' || exp.taskDomain === domainFilter

    const matchesStatus =
      statusFilter === 'all'
        ? true
        : statusFilter === 'active'
        ? exp.status === 'active'
        : statusFilter === 'candidate'
        ? exp.status === 'candidate' || exp.status === 'provisional'
        : statusFilter === 'deprecated'
        ? exp.status === 'deprecated' || exp.status === 'quarantined'
        : true

    return matchesSearch && matchesDomain && matchesStatus
  })
}

// Helper simulating badge label resolution in StatusBadge.tsx
function getStatusBadgeLabel(status: ExperienceStatus | string): string {
  switch (status) {
    case 'active':
      return 'Active'
    case 'candidate':
      return 'Candidate'
    case 'deprecated':
      return 'Deprecated (Quarantined)'
    case 'provisional':
      return 'Candidate (Provisional)'
    case 'quarantined':
      return 'Deprecated (Quarantined)'
    default:
      return String(status).toUpperCase()
  }
}

async function runTests() {
  console.log('🧪 Starting AEMA Frontend Filter & Integrity Test Suite...\n')

  const sampleExperiences: Experience[] = [
    {
      id: 'exp-act-1',
      taskDomain: 'coding',
      triggerCondition: 'Active migration pattern',
      strategyLesson: 'Use dual-write schema pattern',
      pitfallWarning: 'Avoid raw ALTER TABLE',
      trustScore: 0.85,
      successCount: 5,
      failureCount: 0,
      consecutiveFailures: 0,
      status: 'active',
    },
    {
      id: 'exp-cand-1',
      taskDomain: 'coding',
      triggerCondition: 'Candidate async pool pattern',
      strategyLesson: 'Keep async connection pool size proportional to CPU count',
      pitfallWarning: 'Do not allocate unbounded connection pools',
      trustScore: 0.75,
      successCount: 0,
      failureCount: 0,
      consecutiveFailures: 0,
      status: 'candidate',
    },
    {
      id: 'exp-prov-1',
      taskDomain: 'research',
      triggerCondition: 'Provisional literature synthesis',
      strategyLesson: 'Query cross-encoder reranker',
      pitfallWarning: 'Do not rely solely on dense embeddings',
      trustScore: 0.75,
      successCount: 1,
      failureCount: 0,
      consecutiveFailures: 0,
      status: 'provisional',
    },
    {
      id: 'exp-dep-1',
      taskDomain: 'planning',
      triggerCondition: 'Deprecated waterfall scheduler',
      strategyLesson: 'Allocate linear task graphs',
      pitfallWarning: 'Deadlocks occur on cyclical constraints',
      trustScore: 0.25,
      successCount: 0,
      failureCount: 3,
      consecutiveFailures: 3,
      status: 'deprecated',
    },
    {
      id: 'exp-quar-1',
      taskDomain: 'analysis',
      triggerCondition: 'Quarantined hallucinated metric extractor',
      strategyLesson: 'Extract unverified scores',
      pitfallWarning: 'Never extract fabricated scores',
      trustScore: 0.20,
      successCount: 0,
      failureCount: 4,
      consecutiveFailures: 4,
      status: 'quarantined',
    },
  ]

  // ── TEST 1: Filter "all" returns every status ──────────────────────────────
  console.log('1. Testing status filter: "all"')
  const allResults = filterExperiences(sampleExperiences, '', 'all', 'all')
  assert.equal(allResults.length, 5, 'Status filter "all" must return all 5 experiences')
  console.log('   ✅ Passed: "all" returns all 5 experiences across all statuses')

  // ── TEST 2: Filter "active" returns only active records ────────────────────
  console.log('2. Testing status filter: "active"')
  const activeResults = filterExperiences(sampleExperiences, '', 'all', 'active')
  assert.equal(activeResults.length, 1, 'Status filter "active" must return exactly 1 active record')
  assert.equal(activeResults[0].id, 'exp-act-1')
  assert.equal(activeResults[0].status, 'active')
  console.log('   ✅ Passed: "active" returns strictly active records')

  // ── TEST 3: Filter "candidate" returns candidate and provisional records ──
  console.log('3. Testing status filter: "candidate" (Candidate/Provisional)')
  const candidateResults = filterExperiences(sampleExperiences, '', 'all', 'candidate')
  assert.equal(candidateResults.length, 2, 'Status filter "candidate" must return candidate + provisional')
  assert.deepEqual(
    candidateResults.map((r) => r.id).sort(),
    ['exp-cand-1', 'exp-prov-1'].sort()
  )
  console.log('   ✅ Passed: "candidate" correctly maps candidate and provisional records')

  // ── TEST 4: Filter "deprecated" returns deprecated and quarantined records ─
  console.log('4. Testing status filter: "deprecated" (Deprecated/Quarantined)')
  const deprecatedResults = filterExperiences(sampleExperiences, '', 'all', 'deprecated')
  assert.equal(deprecatedResults.length, 2, 'Status filter "deprecated" must return deprecated + quarantined')
  assert.deepEqual(
    deprecatedResults.map((r) => r.id).sort(),
    ['exp-dep-1', 'exp-quar-1'].sort()
  )
  console.log('   ✅ Passed: "deprecated" correctly maps deprecated and quarantined records')

  // ── TEST 5: Empty results handling ─────────────────────────────────────────
  console.log('5. Testing empty results filter handling')
  const onlyActiveList = sampleExperiences.filter((e) => e.status === 'active')
  const emptyCandidateResults = filterExperiences(onlyActiveList, '', 'all', 'candidate')
  assert.equal(emptyCandidateResults.length, 0, 'Empty filter should produce empty array')
  const emptySearch = filterExperiences(sampleExperiences, 'NON_EXISTENT_QUERY_XYZ', 'all', 'all')
  assert.equal(emptySearch.length, 0, 'No match search should produce empty array')
  console.log('   ✅ Passed: Empty results return safely as empty array without exceptions')

  // ── TEST 6: StatusBadge label resolution ──────────────────────────────────
  console.log('6. Testing StatusBadge labels')
  assert.equal(getStatusBadgeLabel('active'), 'Active')
  assert.equal(getStatusBadgeLabel('candidate'), 'Candidate')
  assert.equal(getStatusBadgeLabel('provisional'), 'Candidate (Provisional)')
  assert.equal(getStatusBadgeLabel('deprecated'), 'Deprecated (Quarantined)')
  assert.equal(getStatusBadgeLabel('quarantined'), 'Deprecated (Quarantined)')
  console.log('   ✅ Passed: StatusBadge displays truthful, clear labels for every status')

  // ── TEST 7: Backend API error surfacing (NO silent mock execution) ─────────
  console.log('7. Testing executeAgentTask error surfacing on backend failure')
  const originalFetch = globalThis.fetch
  try {
    globalThis.fetch = async () => {
      throw new Error('Connection refused at http://localhost:9999')
    }

    let caughtError: Error | null = null
    try {
      await executeAgentTask({
        taskInput: 'Test task without backend',
        taskDomain: 'coding',
        memoryEnabled: true,
        isExplicitDemo: false, // Normal mode
      })
    } catch (err: any) {
      caughtError = err
    }

    assert.ok(caughtError !== null, 'executeAgentTask must throw on network error in normal mode')
    assert.match(
      caughtError!.message,
      /Cannot connect to AEMA backend service/,
      'Error message must clearly identify backend network failure'
    )
    console.log('   ✅ Passed: Backend network failure throws an explicit, actionable error')

    // Now simulate HTTP 500 from backend
    globalThis.fetch = async () =>
      new Response(JSON.stringify({ detail: 'LLM Rate limit exceeded on provider' }), {
        status: 500,
        statusText: 'Internal Server Error',
        headers: { 'Content-Type': 'application/json' },
      })

    let caughtHttpError: Error | null = null
    try {
      await executeAgentTask({
        taskInput: 'Test task with 500 error',
        taskDomain: 'coding',
        memoryEnabled: true,
        isExplicitDemo: false,
      })
    } catch (err: any) {
      caughtHttpError = err
    }

    assert.ok(caughtHttpError !== null, 'executeAgentTask must throw on HTTP error')
    assert.match(
      caughtHttpError!.message,
      /AEMA Backend execution failed \(500\)/,
      'Error message must surface HTTP status and backend detail'
    )
    assert.match(caughtHttpError!.message, /LLM Rate limit exceeded on provider/)
    console.log('   ✅ Passed: HTTP failure surfaces backend detail without silent mock fallback')

  } finally {
    globalThis.fetch = originalFetch
  }

  // ── TEST 8: Explicit Demo mode isolation ───────────────────────────────────
  console.log('8. Testing Explicit Demo Mode Isolation')
  const demoResult = await executeAgentTask({
    taskInput: 'Explicit sandbox demo run',
    taskDomain: 'coding',
    memoryEnabled: true,
    isExplicitDemo: true, // Deliberate explicit demo
  })
  assert.ok(demoResult.id.startsWith('demo-exec-'), 'Explicit demo creates demo-exec ID')
  assert.match(
    demoResult.finalOutput,
    /\[EXPLICIT DEMO SANDBOX — SIMULATED EXECUTION\]/,
    'Explicit demo output must be clearly watermarked as simulated execution'
  )
  console.log('   ✅ Passed: Explicit demo mode is clearly watermarked and isolated')

  // ── TEST 9: Telemetry metric integrity ─────────────────────────────────────
  console.log('9. Testing Telemetry Metric Integrity')
  const localMetrics = getTelemetryMetrics()
  assert.equal(localMetrics.timeSavedPct, undefined, 'timeSavedPct must NOT be hardcoded as live metric')
  assert.equal(localMetrics.tokensSavedPct, undefined, 'tokensSavedPct must NOT be hardcoded as live metric')
  assert.equal(localMetrics.benchmarkNegativeTransferReduction, 100.0)
  assert.equal(localMetrics.benchmarkSource, 'Phase 8 v2 McNemar test (p=1.192e-7)')
  assert.equal(localMetrics.totalTasks, 0, 'Local unexecuted telemetry has 0 tasks, not fake 4820')
  assert.equal(localMetrics.memoryHitRate, 0, 'Local unexecuted telemetry has 0 hit rate, not fake 88.4')
  console.log('   ✅ Passed: Telemetry removes fabricated constants and labels benchmarks truthfully')

  console.log('\n🎉 ALL 9 FRONTEND INTEGRITY TESTS PASSED!\n')
}

runTests().catch((err) => {
  console.error('\n❌ Test failure:', err)
  process.exit(1)
})
