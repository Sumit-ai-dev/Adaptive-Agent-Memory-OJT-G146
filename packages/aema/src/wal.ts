/**
 * AEMA Write-Ahead Log (WAL)
 * Side-effect-free append-only audit trail inspired by MemPalace architecture.
 * Immutably logs every memory mutation, trust score decay, and quarantine trigger.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import type { OutcomeType } from './types.js';

export interface WALEntry {
  timestamp: string;
  eventType: 'STORE' | 'FEEDBACK' | 'QUARANTINE' | 'DEDUP' | 'PRUNE';
  experienceId: string;
  domain?: string;
  outcome?: OutcomeType;
  previousTrust?: number;
  newTrust?: number;
  quarantined: boolean;
  metadata?: Record<string, unknown>;
}

function getDefaultWALDir(): string {
  const homeDir = os.homedir();
  return path.join(homeDir, '.aema', 'wal');
}

export class WriteAheadLog {
  private walDir: string;
  private walFile: string;
  private initialized = false;

  constructor(customDir?: string) {
    this.walDir = customDir ?? getDefaultWALDir();
    this.walFile = path.join(this.walDir, 'write_log.jsonl');
  }

  private ensureDir(): void {
    if (this.initialized) return;
    try {
      if (!fs.existsSync(this.walDir)) {
        fs.mkdirSync(this.walDir, { recursive: true, mode: 0o700 });
      }
      this.initialized = true;
    } catch {
      // In restricted environments, silently proceed
    }
  }

  /**
   * Append an immutable audit entry to write-ahead log.
   */
  log(entry: Omit<WALEntry, 'timestamp'>): void {
    try {
      this.ensureDir();
      const record: WALEntry = {
        timestamp: new Date().toISOString(),
        ...entry,
      };
      const line = JSON.stringify(record) + '\n';
      fs.appendFileSync(this.walFile, line, { encoding: 'utf-8', mode: 0o600 });
    } catch {
      // Side-effect-free: WAL failure must never crash core agent memory execution
    }
  }

  /**
   * Read recent WAL audit entries.
   */
  getRecent(limit = 50): WALEntry[] {
    try {
      if (!fs.existsSync(this.walFile)) return [];
      const content = fs.readFileSync(this.walFile, 'utf-8');
      const lines = content.trim().split('\n').filter(Boolean);
      return lines
        .slice(-limit)
        .map((l) => JSON.parse(l) as WALEntry)
        .reverse();
    } catch {
      return [];
    }
  }

  /**
   * Clear the WAL (for testing or reset).
   */
  clear(): void {
    try {
      if (fs.existsSync(this.walFile)) {
        fs.unlinkSync(this.walFile);
      }
    } catch {
      // Ignore
    }
  }
}

export const globalWAL = new WriteAheadLog();
