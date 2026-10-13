#!/usr/bin/env node
/**
 * AEMA CLI: Command-Line Interface for Adaptive Experience Memory Agent
 * Enhanced with MemPalace-inspired dedup, audit, and WAL diagnostics.
 */

import { AEMAClient } from './client.js';
import {
  calculateAsymmetricEMA,
  computeQuarantineSteps,
  DEFAULT_ALPHA,
  DEFAULT_BETA,
  DEFAULT_QUARANTINE_THRESHOLD,
} from './trust.js';

const client = new AEMAClient();

function printHelp() {
  console.log(`
AEMA: Reliability-Aware Experiential Memory for AI Agents
Version: 0.1.0

Usage:
  aema <command> [options]
  npx aema-mcp                  # Start MCP Server on stdio (for Claude/Cursor)

Commands:
  status                        Display current memory trust parameters and quarantine health
  audit                         Run comprehensive memory bank health audit and negative transfer risk
  dedup [--dry-run] [--thresh]  Scan and deduplicate redundant memory traces
  wal [--limit <n>]             View immutable Write-Ahead Log audit trail
  simulate <successes> <fails>  Simulate A-EMA trajectory from initial trust 1.0
  version                       Print version information
  help                          Show this help message

Options:
  --alpha <val>                 Smoothing parameter for success (default: 0.85)
  --beta <val>                  Decay parameter for failure (default: 0.70)
  --threshold <val>             Theorem 1 quarantine cutoff (default: 0.35)
`);
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'help';

  switch (command) {
    case 'status': {
      const quarantined = client.getQuarantined();
      const kStar = computeQuarantineSteps(1.0, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA);
      console.log(`\n=== AEMA Experiential Memory System ===`);
      console.log(`Alpha (Success Factor):      ${DEFAULT_ALPHA}`);
      console.log(`Beta (Failure Penalty):       ${DEFAULT_BETA}`);
      console.log(`Quarantine Threshold:         ${DEFAULT_QUARANTINE_THRESHOLD}`);
      console.log(`Theorem 1 Quarantine Steps:   ${kStar} consecutive failures`);
      console.log(`Active Quarantined Memories:  ${quarantined.length}`);
      console.log(`Status:                       READY\n`);
      break;
    }

    case 'audit': {
      const report = client.audit();
      console.log(`\n=== AEMA Memory Bank Health Audit ===`);
      console.log(`Health Status:               ${report.healthStatus}`);
      console.log(`Total Memories:              ${report.totalMemories}`);
      console.log(`Average Trust Score:         ${(report.averageTrustScore * 100).toFixed(1)}%`);
      console.log(`Quarantined Count:           ${report.quarantinedCount} (${(report.quarantineRatio * 100).toFixed(1)}%)`);
      console.log(`Negative Transfer Risk:      ${(report.negativeTransferRiskScore * 100).toFixed(1)}%`);
      console.log(`\nRecommendations:`);
      for (const rec of report.recommendations) {
        console.log(`  - ${rec}`);
      }
      console.log('');
      break;
    }

    case 'dedup': {
      const isDryRun = args.includes('--dry-run');
      const threshIdx = args.indexOf('--thresh');
      const threshold = threshIdx !== -1 && args[threshIdx + 1] ? parseFloat(args[threshIdx + 1]) : 0.85;

      const res = client.dedup({ threshold, dryRun: isDryRun });
      console.log(`\n=== AEMA Deduplication Sweep ===`);
      console.log(`Total Checked:               ${res.totalChecked}`);
      console.log(`Duplicates Found:            ${res.duplicatesFound}`);
      console.log(`Merged Memories:             ${res.mergedCount}`);
      console.log(`Mode:                        ${isDryRun ? 'DRY RUN' : 'APPLIED'}\n`);
      break;
    }

    case 'wal': {
      const limitIdx = args.indexOf('--limit');
      const limit = limitIdx !== -1 && args[limitIdx + 1] ? parseInt(args[limitIdx + 1], 10) : 10;
      const entries = client.getWAL(limit);

      console.log(`\n=== AEMA Write-Ahead Log (WAL) Audit Trail ===`);
      if (entries.length === 0) {
        console.log(`No WAL entries recorded yet.`);
      } else {
        for (const e of entries) {
          console.log(`[${e.timestamp}] ${e.eventType} on ${e.experienceId} | outcome=${e.outcome || 'N/A'} | trust=${e.newTrust !== undefined ? (e.newTrust * 100).toFixed(1) + '%' : 'N/A'}`);
        }
      }
      console.log('');
      break;
    }

    case 'simulate': {
      const successes = parseInt(args[1] || '0', 10);
      const failures = parseInt(args[2] || '3', 10);
      let score = 1.0;
      console.log(`\nSimulating A-EMA Trust Trajectory (Initial Score = 1.000):`);
      console.log(`---------------------------------------------------------`);

      for (let i = 1; i <= successes; i++) {
        const res = calculateAsymmetricEMA(score, 'success');
        console.log(`Trial +${i} [SUCCESS]: ${(score * 100).toFixed(1)}% -> ${(res.newScore * 100).toFixed(1)}%`);
        score = res.newScore;
      }

      for (let j = 1; j <= failures; j++) {
        const res = calculateAsymmetricEMA(score, 'failure');
        const qNotice = res.isQuarantined ? ' -> [QUARANTINED]' : '';
        console.log(`Trial -${j} [FAILURE]: ${(score * 100).toFixed(1)}% -> ${(res.newScore * 100).toFixed(1)}%${qNotice}`);
        score = res.newScore;
      }
      console.log(`\nFinal Trust Score: ${(score * 100).toFixed(1)}% (Quarantined: ${score < DEFAULT_QUARANTINE_THRESHOLD})\n`);
      break;
    }

    case 'version':
    case '-v':
    case '--version': {
      console.log('aema v0.1.0');
      break;
    }

    case 'help':
    case '--help':
    default: {
      printHelp();
      break;
    }
  }
}

main().catch((err) => {
  console.error('[AEMA CLI Error]:', err.message);
  process.exit(1);
});
