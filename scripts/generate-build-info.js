#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DIST_DIR = path.resolve(__dirname, '..', 'src', 'neuron_client', 'dist');
const MANIFEST_PATH = path.join(DIST_DIR, '.vite', 'manifest.json');
const BUILD_INFO_PATH = path.join(DIST_DIR, 'build-info.json');

function generateBuildInfo() {
  try {
    // Read the Vite manifest
    if (!fs.existsSync(MANIFEST_PATH)) {
      console.error('Vite manifest not found at:', MANIFEST_PATH);
      process.exit(1);
    }

    const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));

    // Extract main entry point assets
    const mainEntry = manifest['src/main.tsx'] || manifest['index.html'];
    if (!mainEntry) {
      console.error('Main entry point not found in manifest');
      process.exit(1);
    }

    // Create a hash based on the main JS and CSS files
    const assets = {
      js: mainEntry.file,
      css: mainEntry.css ? mainEntry.css[0] : null
    };

    // Extract hash from the main JS filename (e.g., index-B6LUCei6.js -> B6LUCei6)
    const jsMatch = assets.js.match(/index-([a-zA-Z0-9]+)\.js$/);
    const assetHash = jsMatch ? jsMatch[1] : crypto.createHash('sha256').update(`${assets.js}${assets.css || ''}`).digest('hex').substring(0, 8);

    const buildInfo = {
      assetHash,
      assets,
      timestamp: new Date().toISOString(),
      buildTime: Date.now(),
      gitCommit: process.env.GIT_COMMIT || null
    };

    // Write build info file
    fs.writeFileSync(BUILD_INFO_PATH, JSON.stringify(buildInfo, null, 2));
    console.log('Generated build-info.json with hash:', assetHash);

  } catch (error) {
    console.error('Error generating build info:', error);
    process.exit(1);
  }
}

generateBuildInfo();
