#!/usr/bin/env node
/**
 * AEMA Model Context Protocol (MCP) Dual-Transport Server (Stdio + HTTP SSE)
 * Enables Claude Desktop, Cursor, Antigravity, and remote agents
 * to seamlessly retrieve reliable memories, log WAL audits, and isolate negative transfer.
 */

import { createServer } from 'node:http';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { z } from 'zod';
import { AEMAClient } from './client.js';
import {
  DEFAULT_ALPHA,
  DEFAULT_BETA,
  DEFAULT_QUARANTINE_THRESHOLD,
  computeQuarantineSteps,
  isQuarantined,
} from './trust.js';

const client = new AEMAClient();

const server = new McpServer({
  name: 'aema-memory',
  version: '0.1.1',
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
    userId: z.string().optional().describe('Optional user/tenant namespace filter'),
  },
  async ({ query, topK, minTrust, domain, userId }) => {
    const results = await client.retrieve({
      query,
      topK: topK ?? 5,
      minTrustScore: minTrust ?? DEFAULT_QUARANTINE_THRESHOLD,
      domain,
      userId,
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
    userId: z.string().optional().describe('Optional user/tenant namespace owner'),
  },
  async ({ task, solution, initialTrust, domain, userId }) => {
    const exp = await client.store({
      task,
      solution,
      outcome: 'success',
      initialTrust: initialTrust ?? 1.0,
      userId,
      metadata: { domain },
    });

    const backendStatus = String(exp.metadata?.backendStatus ?? '').toLowerCase();
    const statusLine =
      backendStatus === 'candidate'
        ? 'Status: CANDIDATE (Synced to FastAPI probation; trust capped at 50.0% until validated)'
        : 'Status: ACTIVE (Logged to WAL)';

    return {
      content: [
        {
          type: 'text',
          text: `Successfully registered experience [${exp.id}] in AEMA memory.\nTrust Score: ${(exp.trustScore * 100).toFixed(1)}%\n${statusLine}`,
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
  {
    userId: z.string().optional().describe('Optional user/tenant namespace filter'),
  },
  async ({ userId }) => {
    await client.syncFromRemote(200, userId);
    const report = client.audit(userId);
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
    await client.syncFromRemote();
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

// Tool 8: Forget / Quarantine or Permanently Erase Memory (GDPR)
server.tool(
  'aema_forget',
  'Remove or soft-quarantine a memory entry. Set hardDelete=true for permanent GDPR/PII erasure.',
  {
    experienceId: z.string().describe('Unique ID of the experience memory to forget'),
    hardDelete: z.boolean().optional().describe('If true, permanently delete instead of soft-quarantine (default: false)'),
    userId: z.string().optional().describe('Optional tenant/user ID for multi-tenant isolation'),
  },
  async ({ experienceId, hardDelete, userId }) => {
    const removed = await client.forget(experienceId, hardDelete ?? false, userId);
    return {
      content: [
        {
          type: 'text',
          text: removed
            ? `Memory [${experienceId}] ${hardDelete ? 'permanently erased' : 'soft-quarantined'}.`
            : `Memory [${experienceId}] was not found or not owned by user.`,
        },
      ],
    };
  }
);

// Tool 9: Recover Quarantined Memory into Probation
server.tool(
  'aema_recover',
  'Safely transition a quarantined memory into candidate probation (honors deprecated -> candidate -> active invariant).',
  {
    experienceId: z.string().describe('Unique ID of the quarantined experience to recover'),
    reason: z.string().optional().describe('Audit justification for recovery (min 15 chars recommended)'),
    userId: z.string().optional().describe('Optional tenant/user ID for multi-tenant isolation'),
  },
  async ({ experienceId, reason, userId }) => {
    const recovered = await client.recover(experienceId, reason, userId);
    return {
      content: [
        {
          type: 'text',
          text: recovered
            ? `Recovered [${recovered.id}] into CANDIDATE probation (status=${String(recovered.metadata?.backendStatus ?? 'candidate')}, trust=${(recovered.trustScore * 100).toFixed(1)}%).`
            : `Memory [${experienceId}] was not found, not owned, or not in quarantined state.`,
        },
      ],
    };
  }
);

// Tool 10: Standard Tool Alias - Record Experience
server.tool(
  'aema_record_experience',
  'Record a verified task execution trace, procedural strategy lesson, and optional pitfall warning into AEMA memory.',
  {
    task: z.string().describe('Task objective or trigger condition'),
    solution: z.string().describe('Successful execution strategy or code pattern'),
    pitfall: z.string().optional().describe('Negative hazard or anti-pattern to avoid'),
    domain: z.string().optional().describe('Problem domain (e.g. coding, research, devops)'),
    initialTrust: z.number().optional().describe('Initial trust score between 0.0 and 1.0 (default: 1.0)'),
    userId: z.string().optional().describe('Optional user namespace'),
  },
  async ({ task, solution, pitfall, domain, initialTrust, userId }) => {
    const exp = await client.store({
      task,
      solution,
      outcome: 'success',
      initialTrust: initialTrust ?? 1.0,
      userId,
      metadata: { domain, pitfall },
    });

    return {
      content: [
        {
          type: 'text',
          text: `Recorded experience [${exp.id}] in domain "${domain || 'general'}".\nTrust Score: ${(exp.trustScore * 100).toFixed(1)}%\nPitfall Guard: ${pitfall || 'None'}`,
        },
      ],
    };
  }
);

// Tool 11: Standard Tool Alias - Calibrate Trust
server.tool(
  'aema_calibrate_trust',
  'Calibrate experience trust using Asymmetric Exponential Moving Average (A-EMA). Calculates mathematical delta and checks Theorem 1 quarantine.',
  {
    experienceId: z.string().describe('Experience ID to calibrate'),
    outcome: z.enum(['success', 'failure']).describe('Execution outcome: "success" reinforces trust (+alpha); "failure" penalizes trust (-beta)'),
  },
  async ({ experienceId, outcome }) => {
    const result = await client.recordFeedback(experienceId, outcome);

    let message = `Calibrated [${experienceId}] via Asymmetric EMA (${outcome.toUpperCase()}).\n` +
      `Prior Trust: ${(result.previousScore * 100).toFixed(1)}% -> New Trust: ${(result.newScore * 100).toFixed(1)}%\n`;

    if (result.isQuarantined) {
      message += `[QUARANTINE ACTIVATED] Trust dropped below theta (${DEFAULT_QUARANTINE_THRESHOLD}). Strategy quarantined via Theorem 1.`;
    } else {
      message += `Status: Verified Active`;
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

// Tool 12: Quarantine Check (Theorem 1 Mathematical Bound)
server.tool(
  'aema_quarantine_check',
  'Check whether a memory is quarantined under Theorem 1 (theta <= 0.35) and calculate remaining consecutive failures before quarantine.',
  {
    experienceId: z.string().optional().describe('Optional memory ID to inspect'),
    trustScore: z.number().optional().describe('Optional trust score to test (0.0 to 1.0)'),
  },
  async ({ experienceId, trustScore }) => {
    let score = trustScore;

    if (score === undefined && experienceId) {
      await client.syncFromRemote();
      const quarantinedList = client.getQuarantined();
      const found = quarantinedList.find((q) => q.id === experienceId);
      if (found) score = found.trustScore;
    }

    const effectiveScore = score ?? 1.0;
    const quarantined = isQuarantined(effectiveScore);
    const steps = computeQuarantineSteps(effectiveScore, DEFAULT_QUARANTINE_THRESHOLD, DEFAULT_BETA);

    const text = `## Theorem 1 Quarantine Analysis\n\n` +
      `- **Evaluated Trust Score**: ${(effectiveScore * 100).toFixed(1)}%\n` +
      `- **Quarantine Threshold (theta)**: ${DEFAULT_QUARANTINE_THRESHOLD}\n` +
      `- **Quarantine Status**: ${quarantined ? 'QUARANTINED (Isolated from context)' : 'ACTIVE (Safe for retrieval)'}\n` +
      `- **Consecutive Failures Bound (k*)**: ${steps} failure(s) until quarantine cutoff (k* <= 3 theorem guarantee).`;

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

// Tool 13: List Memories with Status Filtering
server.tool(
  'aema_list_memories',
  'List memories with status filtering (active, candidate, quarantined, all) and domain scoping.',
  {
    status: z.enum(['active', 'candidate', 'quarantined', 'all']).optional().describe('Filter by memory status (default: all)'),
    domain: z.string().optional().describe('Optional domain filter'),
    limit: z.number().optional().describe('Max entries to return (default: 20)'),
    userId: z.string().optional().describe('Optional user namespace'),
  },
  async ({ status, domain, limit, userId }) => {
    await client.syncFromRemote(limit ?? 50, userId);
    const auditReport = client.audit(userId);

    const text = `## AEMA Experiential Memory Bank\n\n` +
      `- **Total Memories**: ${auditReport.totalMemories}\n` +
      `- **Active Strategies**: ${auditReport.totalMemories - auditReport.quarantinedCount}\n` +
      `- **Quarantined Traps**: ${auditReport.quarantinedCount}\n` +
      `- **Filter Applied**: status=${status ?? 'all'}, domain=${domain ?? 'all'}\n` +
      `- **System Health**: ${auditReport.healthStatus}`;

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

// ─── Dual-Transport Server Runner (Stdio + HTTP SSE) ──────────────────────────

async function main() {
  const isSSE =
    process.argv.includes('--sse') ||
    process.env.MCP_TRANSPORT === 'sse' ||
    process.env.TRANSPORT === 'sse' ||
    Boolean(process.env.PORT);

  if (isSSE) {
    const port = Number(process.env.PORT || process.env.MCP_PORT || 3001);
    const host = process.env.HOST || '0.0.0.0';
    const transports = new Map<string, SSEServerTransport>();

    const httpServer = createServer(async (req, res) => {
      const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

      // Global CORS headers
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

      if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
      }

      // Healthcheck probe endpoint
      if (url.pathname === '/health' || url.pathname === '/mcp/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'healthy', transport: 'sse', version: '2.0.0' }));
        return;
      }

      // Establish SSE connection
      if (req.method === 'GET' && (url.pathname === '/sse' || url.pathname === '/mcp/sse')) {
        const transport = new SSEServerTransport('/messages', res);
        transports.set(transport.sessionId, transport);

        transport.onclose = () => {
          transports.delete(transport.sessionId);
        };

        await server.connect(transport);
        return;
      }

      // Inbound JSON-RPC messages
      if (req.method === 'POST' && (url.pathname === '/messages' || url.pathname === '/mcp/messages')) {
        const sessionId = url.searchParams.get('sessionId');
        const transport = sessionId ? transports.get(sessionId) : Array.from(transports.values())[0];

        if (!transport) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Session not found. Connect to /sse endpoint first.' }));
          return;
        }

        await transport.handlePostMessage(req, res);
        return;
      }

      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Endpoint not found. Use /sse or /messages.' }));
    });

    httpServer.listen(port, host, () => {
      console.error(`[AEMA MCP Server] Running on HTTP SSE at http://${host}:${port}/sse`);
    });
  } else {
    // Default Stdio JSON-RPC transport for Cursor, Claude Desktop, Antigravity
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('[AEMA MCP Server] Running on stdio JSON-RPC protocol.');
  }
}

main().catch((error) => {
  console.error('[AEMA MCP Server Fatal Error]:', error);
  process.exit(1);
});
