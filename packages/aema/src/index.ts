/**
 * AEMA: Reliability-Aware Experiential Memory for AI Agents
 * 
 * Asymmetric Exponential Moving Average (A-EMA) mathematically isolates
 * negative transfer in agentic workflows by coupling empirical reliability
 * with semantic relevance.
 * 
 * Native Support:
 * - Anthropic Claude Desktop & Claude Code (MCP)
 * - Cursor IDE (MCP & .cursor-plugin)
 * - OpenAI GPT-4o, o1, o3-mini (Function Calling)
 * - xAI Grok-2, Grok-3 (Function Calling)
 * - Google Gemini 1.5, 2.0 (Function Declarations)
 * 
 * Authors: Sumit Das, Sakshi Dattaprasad Kasat
 * License: MIT
 */

export * from './types.js';
export * from './trust.js';
export * from './client.js';
export * from './wal.js';
export * from './dedup.js';
export * from './audit.js';
export * from './adapters.js';

// Default export
import { AEMAClient } from './client.js';
export default AEMAClient;
