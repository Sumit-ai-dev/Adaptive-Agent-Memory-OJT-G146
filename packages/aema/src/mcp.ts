#!/usr/bin/env node
/**
 * AEMA Model Context Protocol (MCP) Stdio Server
 * Enables Claude Desktop, Cursor, Windsurf, and custom AI agents
 * to seamlessly retrieve reliable memories, log WAL audits, and isolate negative transfer.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { AEMAClient } from './client.js';
import {
  DEFAULT_ALPHA,
  DEFAULT_BETA,
  DEFAULT_QUARANTINE_THRESHOLD,
  computeQuarantineSteps,
} from './trust.js';

const client = new AEMAClient();

const server = new McpServer({
  name: 'aema-memory',
  version: '0.1.0',
});

// Tool 1: Retrieve Reliable Memories
server.tool(
  'aema_retrieve',
  'Retrieve reliable, non-quarantined experiential memories for an agent task. Filters out negative transfer and harmful experiences using Theorem 1 quarantine cutoff.',
  {
    query: z.string().describe('The task description or query context to search for in experiential memory'),
    topK: z.number().optional().describe('Maximum number of memories to return (default: 5)'),
    minTrust: z.number().optional().describe('Minimum trust threshold for retrieved memories (default: 0.35)'),
    domain: z.string().optional().describe('Optional scope/domain filter (e.g. coding, research, devops)'),
  },
  async ({ query, topK, minTrust, domain }) => {
    const results = await client.retrieve({
      query,
      topK: topK ?? 5,
      minTrustScore: minTrust ?? DEFAULT_QUARANTINE_THRESHOLD,
      domain,
    });

    if (results.length === 0) {
      return {
        content: [
          {
            type: 'text',
            text: `No verified reliable experiences found for query: "${query}". (Unverified or quarantined memories were safely omitted to prevent negative transfer).`,
          },
        ],
      };
    }

    const formatted = results.map((r, i) => {
      return `### Memory [${i + 1}] (Trust: ${(r.experience.trustScore * 100).toFixed(1)}%, Effective Rank: ${r.effectiveScore.toFixed(3)})\n` +
        `**ID**: ${r.experience.id}\n` +
        `**Task**: ${r.experience.task}\n` +
        `**Verified Solution**:\n\`\`\`\n${r.experience.solution}\n\`\`\`\n` +
        `**Reliability Status**: ${r.isReliable ? 'VERIFIED RELIABLE' : 'UNVERIFIED'}`;
    }).join('\n\n');

    return {
      content: [
        {
          type: 'text',
          text: `Found ${results.length} reliable experiential memories:\n\n${formatted}`,
        },
      ],
    };
  }
);

// Tool 2: Store New Experience
server.tool(
  'aema_store',
  'Store a new task execution trace or verified solution in AEMA experiential memory with an initial trust score and immutable WAL entry.',
  {
    task: z.string().describe('Task objective or problem description'),
    solution: z.string().describe('Successful solution, code snippet, or execution trace'),
    initialTrust: z.number().optional().describe('Initial trust score between 0.0 and 1.0 (default: 1.0)'),
    domain: z.string().optional().describe('Problem domain or categorization (e.g., coding, research, devops)'),
  },
  async ({ task, solution, initialTrust, domain }) => {
    const exp = await client.store({
      task,
      solution,
      outcome: 'success',
      initialTrust: initialTrust ?? 1.0,
      metadata: { domain },
    });

    return {
      content: [
        {
          type: 'text',
          text: `Successfully registered experience [${exp.id}] in AEMA memory.\nInitial Trust Score: ${(exp.trustScore * 100).toFixed(1)}%\nStatus: ACTIVE (Logged to WAL)`,
        },
      ],
    };
  }
);

// Tool 3: Record Feedback (Trust Decay / Recovery)
server.tool(
  'aema_feedback',
  'Update experience trust score following execution using Asymmetric Exponential Moving Average (A-EMA). Automatically activates Theorem 1 quarantine if score decays below 0.35.',
  {
    experienceId: z.string().describe('Unique ID of the experience memory'),
    outcome: z.enum(['success', 'failure']).describe('Execution outcome: "success" reinforces trust; "failure" penalizes trust'),
  },
  async ({ experienceId, outcome }) => {
    const result = await client.recordFeedback(experienceId, outcome);

    let message = `Recorded ${outcome.toUpperCase()} for [${experienceId}].\n` +
      `Previous Score: ${(result.previousScore * 100).toFixed(1)}% -> New Score: ${(result.newScore * 100).toFixed(1)}%\n`;

    if (result.isQuarantined) {
      message += `\n[QUARANTINE ALERT] Trust score dropped below threshold (${DEFAULT_QUARANTINE_THRESHOLD}). Experience is now QUARANTINED to prevent negative transfer.`;
    } else {
      message += `Status: ACTIVE (Reliable)`;
    }

    return {
      content: [
        {
          type: 'text',
          text: message,
        },
      ],
    };
  }
);

// Tool 4: System Audit & Negative Transfer Risk Index (MemPalace style)
server.tool(
  'aema_audit',
  'Perform full health diagnostics on the agent memory bank: compute average trust, quarantine ratios, domain distributions, and negative transfer risk score.',
  {},
  async () => {
    const report = client.audit();
    const formatted = `## AEMA Experiential Memory Bank Audit\n\n` +
      `- **Overall Health**: ${report.healthStatus}\n` +
      `- **Total Memories**: ${report.totalMemories}\n` +
      `- **Average Trust Score**: ${(report.averageTrustScore * 100).toFixed(1)}%\n` +
      `- **Quarantined Count**: ${report.quarantinedCount} (${(report.quarantineRatio * 100).toFixed(1)}%)\n` +
      `- **Negative Transfer Risk Index**: ${(report.negativeTransferRiskScore * 100).toFixed(1)}% (Lower is safer)\n\n` +
      `### Recommendations:\n${report.recommendations.map((r) => `- ${r}`).join('\n')}`;

    return {
      content: [
        {
          type: 'text',
          text: formatted,
        },
      ],
    };
  }
);

// Tool 5: Deduplication Sweep (MemPalace dedup.py style)
server.tool(
  'aema_dedup',
  'Scan memory bank for redundant or duplicate experiences and merge them, preserving the highest-trust verified solution.',
  {
    threshold: z.number().optional().describe('Jaccard similarity threshold for duplicates (default: 0.85)'),
    dryRun: z.boolean().optional().describe('If true, previews duplicates without deleting them (default: false)'),
    domain: z.string().optional().describe('Optional domain filter'),
  },
  async ({ threshold, dryRun, domain }) => {
    const result = client.dedup({ threshold, dryRun, domain });
    const text = `## AEMA Deduplication Sweep Report\n\n` +
      `- **Total Experiences Checked**: ${result.totalChecked}\n` +
      `- **Duplicates Found**: ${result.duplicatesFound}\n` +
      `- **Merged Count**: ${result.mergedCount}\n` +
      `- **Dry Run**: ${dryRun ? 'YES (No changes applied)' : 'NO (Applied)'}\n` +
      (result.purgedIds.length > 0 ? `\nPurged IDs:\n${result.purgedIds.map((id) => `- ${id}`).join('\n')}` : `\nMemory bank is clean with zero redundant entries.`);

    return {
      content: [
        {
          type: 'text',
          text,
        },
      ],
    };
  }
);

// Tool 6: Write-Ahead Log Inspection (MemPalace wal.py style)
server.tool(
  'aema_wal',
  'Inspect recent immutable Write-Ahead Log audit entries for forensic analysis of memory modifications and quarantine triggers.',
  {
    limit: z.number().optional().describe('Number of recent audit records to retrieve (default: 15)'),
  },
  async ({ limit }) => {
    const entries = client.getWAL(limit ?? 15);
    if (entries.length === 0) {
      return {
        content: [{ type: 'text', text: 'Write-Ahead Log is currently empty.' }],
      };
    }

    const formatted = entries.map((e, idx) => {
      return `[${idx + 1}] **${e.timestamp}** | Event: \`${e.eventType}\` | ID: \`${e.experienceId}\`\n` +
        `  Outcome: ${e.outcome ?? 'N/A'} | Trust: ${e.previousTrust !== undefined ? (e.previousTrust * 100).toFixed(1) + '%' : 'N/A'} -> ${e.newTrust !== undefined ? (e.newTrust * 100).toFixed(1) + '%' : 'N/A'}` +
        ` | Quarantined: ${e.quarantined ? 'YES' : 'NO'}`;
    }).join('\n');

    return {
      content: [
        {
          type: 'text',
          text: `## AEMA Write-Ahead Log (WAL) Audit Trail\n\n${formatted}`,
        },
      ],
    };
  }
);

// Tool 7: Quarantine Status & System Hyperparameters
server.tool(
  'aema_status',
  'Inspect the mathematical parameters and quarantine state of AEMA experiential memory.',
  {},
  async () => {
    const quarantined = client.getQuarantined();
    const stepsToQuarantine = computeQuarantineSteps(1.0, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA);

    const statusText = `## AEMA Experiential Memory System Status\n\n` +
      `- **Success Smoothing Factor (alpha)**: ${DEFAULT_ALPHA}\n` +
      `- **Failure Decay Penalty (beta)**: ${DEFAULT_BETA}\n` +
      `- **Theorem 1 Quarantine Threshold (theta)**: ${DEFAULT_QUARANTINE_THRESHOLD}\n` +
      `- **Consecutive Failures to Quarantine**: ${stepsToQuarantine} steps\n` +
      `- **Quarantined Memories Count**: ${quarantined.length}\n\n` +
      (quarantined.length > 0
        ? `Quarantined IDs:\n${quarantined.map((q) => `- ${q.id} (Trust: ${(q.trustScore * 100).toFixed(1)}%, Task: "${q.task}")`).join('\n')}`
        : `All active memories are operating within verified reliability bounds.`);

    return {
      content: [
        {
          type: 'text',
          text: statusText,
        },
      ],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[AEMA MCP Server] Running on stdio protocol.');
}

main().catch((error) => {
  console.error('[AEMA MCP Server Fatal Error]:', error);
  process.exit(1);
});
