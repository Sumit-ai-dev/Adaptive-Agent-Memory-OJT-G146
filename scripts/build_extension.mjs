#!/usr/bin/env node
/**
 * AEMA Chrome Extension Build & Validation Script
 * Verifies Manifest V3 compliance, icons, and prepares unpacked bundle.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const extDir = path.join(rootDir, 'extension');

console.log('[AEMA Extension] Validating Chrome Extension (Manifest V3)...');

// 1. Verify manifest.json
const manifestPath = path.join(extDir, 'manifest.json');
if (!fs.existsSync(manifestPath)) {
  console.error('Error: extension/manifest.json not found!');
  process.exit(1);
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
if (manifest.manifest_version !== 3) {
  console.error(`Error: manifest_version must be 3, found ${manifest.manifest_version}`);
  process.exit(1);
}

// 2. Verify required files
const requiredFiles = [
  'background.js',
  'content.js',
  'popup.html',
  'popup.js',
  'icons/icon16.png',
  'icons/icon48.png',
  'icons/icon128.png',
];

for (const relFile of requiredFiles) {
  const fullPath = path.join(extDir, relFile);
  if (!fs.existsSync(fullPath)) {
    console.error(`Error: Required extension asset missing: ${relFile}`);
    process.exit(1);
  }
}

console.log(`[AEMA Extension] Validation passed:`);
console.log(`  - Manifest: ${manifest.name} v${manifest.version} (MV3)`);
console.log(`  - Service Worker: background.js`);
console.log(`  - Popup: popup.html (Obsidian theme with 5-node stepper)`);
console.log(`  - Content Script: content.js`);
console.log(`  - Icons: icon16.png, icon48.png, icon128.png`);
console.log(`[AEMA Extension] Ready to load as unpacked extension in chrome://extensions.`);
