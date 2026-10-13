/**
 * AEMA Deduplication Engine
 * Detects and consolidates near-duplicate experiences across memory stores.
 * Inspired by MemPalace dedup.py architecture.
 */

import type { Experience } from './types.js';
import { globalWAL } from './wal.js';

export interface DedupResult {
  totalChecked: number;
  duplicatesFound: number;
  mergedCount: number;
  retainedIds: string[];
  purgedIds: string[];
}

/**
 * Compute Jaccard similarity over word token sets.
 */
function jaccardSimilarity(a: string, b: string): number {
  const setA = new Set(a.toLowerCase().split(/\s+/).filter(Boolean));
  const setB = new Set(b.toLowerCase().split(/\s+/).filter(Boolean));
  if (setA.size === 0 && setB.size === 0) return 1.0;
  if (setA.size === 0 || setB.size === 0) return 0.0;

  let intersection = 0;
  for (const token of setA) {
    if (setB.has(token)) intersection++;
  }
  const union = setA.size + setB.size - intersection;
  return union > 0 ? intersection / union : 0.0;
}

/**
 * Deduplicate an array of experiences.
 * If similarity exceeds threshold (default 0.85), retains the entry with
 * higher trust score / more trials and purges the redundant copy.
 */
export function deduplicateExperiences(
  experiences: Experience[],
  options: {
    similarityThreshold?: number; // default: 0.85
    dryRun?: boolean;
    domain?: string;
  } = {}
): { cleaned: Experience[]; report: DedupResult } {
  const threshold = options.similarityThreshold ?? 0.85;
  const filtered = options.domain
    ? experiences.filter((e) => e.metadata?.domain === options.domain)
    : [...experiences];

  const purgedIds: string[] = [];
  const retainedMap = new Map<string, Experience>();
  const activeList: Experience[] = [];

  for (const current of filtered) {
    let duplicateOf: Experience | null = null;

    for (const existing of activeList) {
      const taskSim = jaccardSimilarity(current.task, existing.task);
      const solSim = jaccardSimilarity(current.solution, existing.solution);
      const combinedSim = 0.5 * taskSim + 0.5 * solSim;

      if (combinedSim >= threshold) {
        duplicateOf = existing;
        break;
      }
    }

    if (!duplicateOf) {
      activeList.push(current);
      retainedMap.set(current.id, current);
    } else {
      // Duplicate found! Keep the richer/higher-trust memory
      if (current.trustScore > duplicateOf.trustScore || current.solution.length > duplicateOf.solution.length) {
        // Current is better; replace duplicateOf
        const idx = activeList.indexOf(duplicateOf);
        if (idx !== -1) activeList[idx] = current;
        retainedMap.delete(duplicateOf.id);
        retainedMap.set(current.id, current);
        purgedIds.push(duplicateOf.id);

        if (!options.dryRun) {
          globalWAL.log({
            eventType: 'DEDUP',
            experienceId: current.id,
            domain: current.metadata?.domain as string | undefined,
            quarantined: current.isQuarantined,
            metadata: { purgedDuplicateId: duplicateOf.id, reason: 'higher_trust_retained' },
          });
        }
      } else {
        // Keep duplicateOf, purge current
        purgedIds.push(current.id);

        if (!options.dryRun) {
          globalWAL.log({
            eventType: 'DEDUP',
            experienceId: duplicateOf.id,
            domain: duplicateOf.metadata?.domain as string | undefined,
            quarantined: duplicateOf.isQuarantined,
            metadata: { purgedDuplicateId: current.id, reason: 'existing_retained' },
          });
        }
      }
    }
  }

  const retainedIds = Array.from(retainedMap.keys());

  return {
    cleaned: activeList,
    report: {
      totalChecked: filtered.length,
      duplicatesFound: purgedIds.length,
      mergedCount: purgedIds.length,
      retainedIds,
      purgedIds,
    },
  };
}
