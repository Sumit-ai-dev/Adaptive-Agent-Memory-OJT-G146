/**
 * Example: Using @sumitaidev/aema in Node.js / TypeScript apps.
 * Works standalone (persisted to ~/.aema/memories.json) or synced with `aema serve`.
 */

import { AEMAClient } from '@sumitaidev/aema';

async function main() {
  const memory = new AEMAClient({
    baseUrl: process.env.AEMA_API_URL || 'http://localhost:8000',
  });

  const saved = await memory.store({
    task: 'Voice TTS speaking raw JSON',
    solution: 'Extract plain spoken summary before calling ElevenLabs/TTS audio stream.',
    metadata: { domain: 'general' },
  });

  const matches = await memory.retrieve({ query: 'Voice TTS JSON', topK: 3 });
  console.log('Retrieved matches:', matches.length);

  // Record verified success or failure (3 consecutive failures trigger Theorem 1 quarantine)
  const update = await memory.recordFeedback(saved.id, 'success');
  console.log('Trust score after feedback:', update.newScore, 'Quarantined:', update.isQuarantined);
}

main().catch(console.error);

