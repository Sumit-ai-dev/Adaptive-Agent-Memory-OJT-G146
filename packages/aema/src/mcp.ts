#!/usr/bin/env node
/**
 * AEMA Model Context Protocol (MCP) Stdio Server
 * Enables Claude Desktop, Cursor, Windsurf, and custom AI agents
 * to seamlessly retrieve reliable memories and isolate negative transfer.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { AEMAClient } from './client.js';
import {
  calculateAsymmetricEMA,
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
  },
  async ({ query, topK, minTrust }) => {
    const results = await client.retrieve({
      query,
      topK: topK ?? 5,
      minTrustScore: minTrust ?? DEFAULT_QUARANTINE_THRESHOLD,
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
  'Store a new task execution trace or verified solution in AEMA experiential memory with an initial trust score.',
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
          text: `Successfully registered experience [${exp.id}] in AEMA memory.\nInitial Trust Score: ${(exp.trustScore * 100).toFixed(1)}%\nStatus: ACTIVE`,
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

// Tool 4: Quarantine Status & Health
server.tool(
  'aema_status',
  'Inspect the current state of AEMA experiential memory, quarantine counts, and mathematical parameter settings.',
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
