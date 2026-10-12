/**
 * AEMA: Reliability-Aware Experiential Memory for AI Agents
 * 
 * Asymmetric Exponential Moving Average (A-EMA) mathematically isolates
 * negative transfer in agentic workflows by coupling empirical reliability
 * with semantic relevance.
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

// Default export
import { AEMAClient } from './client.js';
export default AEMAClient;
