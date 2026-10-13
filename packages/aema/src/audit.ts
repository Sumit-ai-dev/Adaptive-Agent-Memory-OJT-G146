/**
 * AEMA System Audit & Health Diagnostics
 * Computes memory trust distribution, negative transfer risk score,
 * and quarantine ratios. Inspired by MemPalace palace_audit.py.
 */

import type { Experience } from './types.js';
import { DEFAULT_QUARANTINE_THRESHOLD } from './trust.js';

export interface AuditReport {
  totalMemories: number;
  averageTrustScore: number;
  quarantinedCount: number;
  quarantineRatio: number;
  negativeTransferRiskScore: number; // 0.0 (Safe) to 1.0 (Critical)
  domainBreakdown: Record<string, { total: number; avgTrust: number; quarantined: number }>;
  healthStatus: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  recommendations: string[];
}

export function auditMemoryBank(experiences: Experience[]): AuditReport {
  if (experiences.length === 0) {
    return {
      totalMemories: 0,
      averageTrustScore: 1.0,
      quarantinedCount: 0,
      quarantineRatio: 0.0,
      negativeTransferRiskScore: 0.0,
      domainBreakdown: {},
      healthStatus: 'HEALTHY',
      recommendations: ['Memory bank is empty. Ready to ingest initial task traces.'],
    };
  }

  let totalTrust = 0;
  let quarantinedCount = 0;
  const domainBreakdown: Record<string, { total: number; sumTrust: number; quarantined: number }> = {};

  for (const exp of experiences) {
    totalTrust += exp.trustScore;
    if (exp.isQuarantined || exp.trustScore < DEFAULT_QUARANTINE_THRESHOLD) {
      quarantinedCount++;
    }

    const domain = (exp.metadata?.domain as string) || 'default';
    if (!domainBreakdown[domain]) {
      domainBreakdown[domain] = { total: 0, sumTrust: 0, quarantined: 0 };
    }
    domainBreakdown[domain].total += 1;
    domainBreakdown[domain].sumTrust += exp.trustScore;
    if (exp.isQuarantined) {
      domainBreakdown[domain].quarantined += 1;
    }
  }

  const avgTrust = totalTrust / experiences.length;
  const quarantineRatio = quarantinedCount / experiences.length;

  // Negative Transfer Risk: High if there are unquarantined memories near the quarantine border (0.35 - 0.50)
  const borderlineMemories = experiences.filter(
    (e) => !e.isQuarantined && e.trustScore >= 0.35 && e.trustScore <= 0.50
  ).length;
  const negativeTransferRiskScore = Math.min(1.0, (borderlineMemories * 1.5 + quarantinedCount * 0.5) / experiences.length);

  const formattedDomains: Record<string, { total: number; avgTrust: number; quarantined: number }> = {};
  for (const [dom, stats] of Object.entries(domainBreakdown)) {
    formattedDomains[dom] = {
      total: stats.total,
      avgTrust: stats.sumTrust / stats.total,
      quarantined: stats.quarantined,
    };
  }

  const recommendations: string[] = [];
  let healthStatus: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' = 'HEALTHY';

  if (quarantineRatio > 0.4) {
    healthStatus = 'CRITICAL';
    recommendations.push('High concentration of quarantined memories (>40%). Run dedup or prune stale memories.');
  } else if (quarantineRatio > 0.15 || borderlineMemories > 3) {
    healthStatus = 'DEGRADED';
    recommendations.push('Noticeable memory degradation detected. Execute confirmatory trials to restore trust.');
  } else {
    recommendations.push('Experiential memory operating within verified reliability parameters.');
  }

  if (borderlineMemories > 0) {
    recommendations.push(`${borderlineMemories} memories are approaching Theorem 1 quarantine threshold.`);
  }

  return {
    totalMemories: experiences.length,
    averageTrustScore: avgTrust,
    quarantinedCount,
    quarantineRatio,
    negativeTransferRiskScore,
    domainBreakdown: formattedDomains,
    healthStatus,
    recommendations,
  };
}
