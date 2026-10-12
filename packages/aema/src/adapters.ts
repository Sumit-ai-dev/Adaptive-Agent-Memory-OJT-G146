/**
 * Multi-LLM Adapters for AEMA
 * Ready-to-use function calling definitions and handlers for:
 * - OpenAI (GPT-4o, o1, o3-mini)
 * - Grok (xAI Grok-2, Grok-3 via OpenAI-compatible schema)
 * - Google Gemini (Gemini 2.0, 1.5 Pro / Flash via Google GenAI schema)
 * - Anthropic Claude & Cursor (via native MCP stdio protocol)
 */

import { AEMAClient } from './client.js';
import type { OutcomeType } from './types.js';

const client = new AEMAClient();

// ============================================================================
// 1. OpenAI & Grok (xAI) Function Calling Schema
// ============================================================================

export const openAITools = [
  {
    type: 'function' as const,
    function: {
      name: 'aema_retrieve',
      description:
        'Retrieve reliable, non-quarantined experiential memories for an agent task. Automatically isolates negative transfer using Theorem 1 quarantine cutoff.',
      parameters: {
        type: 'object',
        properties: {
          query: {
            type: 'string',
            description: 'Task description or context query to search memories for',
          },
          topK: {
            type: 'number',
            description: 'Maximum number of memories to return (default: 5)',
          },
          minTrust: {
            type: 'number',
            description: 'Minimum trust threshold (default: 0.35)',
          },
          domain: {
            type: 'string',
            description: 'Optional domain/namespace filter (e.g. coding, research)',
          },
        },
        required: ['query'],
      },
    },
  },
  {
    type: 'function' as const,
    function: {
      name: 'aema_store',
      description: 'Store a newly verified task execution trace or solution in experiential memory.',
      parameters: {
        type: 'object',
        properties: {
          task: { type: 'string', description: 'Task objective or problem' },
          solution: { type: 'string', description: 'Verified working solution' },
          initialTrust: { type: 'number', description: 'Initial trust score between 0 and 1 (default: 1.0)' },
          domain: { type: 'string', description: 'Optional domain category' },
        },
        required: ['task', 'solution'],
      },
    },
  },
  {
    type: 'function' as const,
    function: {
      name: 'aema_feedback',
      description: 'Record execution success or failure to trigger A-EMA trust update and quarantine check.',
      parameters: {
        type: 'object',
        properties: {
          experienceId: { type: 'string', description: 'Unique ID of the memory' },
          outcome: {
            type: 'string',
            enum: ['success', 'failure'],
            description: 'Outcome of execution',
          },
        },
        required: ['experienceId', 'outcome'],
      },
    },
  },
  {
    type: 'function' as const,
    function: {
      name: 'aema_audit',
      description: 'Perform memory health diagnostics, calculating average trust, quarantine ratios, and negative transfer risk.',
      parameters: {
        type: 'object',
        properties: {},
      },
    },
  },
];

/**
 * Grok (xAI) uses the exact same tools schema as OpenAI.
 */
export const grokTools = openAITools;

/**
 * Universal dispatcher for OpenAI / Grok tool calls.
 */
export async function handleOpenAIToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<string> {
  switch (name) {
    case 'aema_retrieve': {
      const results = await client.retrieve({
        query: args.query as string,
        topK: (args.topK as number) || 5,
        minTrustScore: (args.minTrust as number) || 0.35,
        domain: args.domain as string | undefined,
      });
      return JSON.stringify(results, null, 2);
    }
    case 'aema_store': {
      const exp = await client.store({
        task: args.task as string,
        solution: args.solution as string,
        initialTrust: (args.initialTrust as number) || 1.0,
        metadata: { domain: args.domain as string | undefined },
      });
      return JSON.stringify(exp, null, 2);
    }
    case 'aema_feedback': {
      const res = await client.recordFeedback(
        args.experienceId as string,
        args.outcome as OutcomeType
      );
      return JSON.stringify(res, null, 2);
    }
    case 'aema_audit': {
      const report = client.audit();
      return JSON.stringify(report, null, 2);
    }
    default:
      throw new Error(`Unknown AEMA tool: ${name}`);
  }
}

// ============================================================================
// 2. Google Gemini Function Declarations Schema
// ============================================================================

export const geminiTools = [
  {
    functionDeclarations: [
      {
        name: 'aema_retrieve',
        description:
          'Retrieve reliable, non-quarantined experiential memories for an agent task. Automatically isolates negative transfer.',
        parameters: {
          type: 'OBJECT',
          properties: {
            query: { type: 'STRING', description: 'Task context query' },
            topK: { type: 'NUMBER', description: 'Number of results to return' },
            minTrust: { type: 'NUMBER', description: 'Minimum trust threshold (default: 0.35)' },
            domain: { type: 'STRING', description: 'Optional domain filter' },
          },
          required: ['query'],
        },
      },
      {
        name: 'aema_store',
        description: 'Store a verified execution trace in experiential memory.',
        parameters: {
          type: 'OBJECT',
          properties: {
            task: { type: 'STRING', description: 'Task description' },
            solution: { type: 'STRING', description: 'Verified solution' },
            initialTrust: { type: 'NUMBER', description: 'Initial trust (0 to 1)' },
            domain: { type: 'STRING', description: 'Domain classification' },
          },
          required: ['task', 'solution'],
        },
      },
      {
        name: 'aema_feedback',
        description: 'Record success/failure to trigger A-EMA trust update.',
        parameters: {
          type: 'OBJECT',
          properties: {
            experienceId: { type: 'STRING', description: 'ID of experience' },
            outcome: { type: 'STRING', description: '"success" or "failure"' },
          },
          required: ['experienceId', 'outcome'],
        },
      },
      {
        name: 'aema_audit',
        description: 'Perform memory bank health audit and negative transfer risk assessment.',
        parameters: {
          type: 'OBJECT',
          properties: {},
        },
      },
    ],
  },
];

/**
 * Dispatcher for Google Gemini function calls.
 */
export async function handleGeminiToolCall(
  name: string,
  args: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const resultJson = await handleOpenAIToolCall(name, args);
  return JSON.parse(resultJson);
}
