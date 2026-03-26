#!/usr/bin/env node

import { readFile, writeFile, mkdir, readdir } from 'fs/promises';
import { exec } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.join(__dirname, '..');

async function renderShayariVideos() {
  try {
    // Read shayari.json
    const shayariPath = path.join(
      'C:/git/youtube-automation/Epic-Stories-All-youtube-automation-shorts/data/shayari/shayari.json'
    );
    const data = await readFile(shayariPath, 'utf-8');
    const shayaris = JSON.parse(data);

    // Take only the first entry
    const entries = shayaris.slice(0, 1);

    console.log(`Found ${shayaris.length} shayaris. Rendering first 10...\n`);

    // Create output directory
    const outDir = path.join(projectRoot, 'out');
    await mkdir(outDir, { recursive: true });

    // Create props temp directory
    const propsDir = path.join(projectRoot, 'props-temp');
    await mkdir(propsDir, { recursive: true });

    // Render each shayari
    for (let i = 0; i < entries.length; i++) {
      const item = entries[i];
      const quote = item.quote;
      const author = item.author;
      const outputPath = path.join(outDir, `shayari-${i + 1}.mp4`);

      console.log(`\n📹 Rendering Shayari ${i + 1}/${entries.length}:`);
      console.log(`   Quote: "${quote.substring(0, 50)}..."`);
      console.log(`   Author: ${author}`);
      console.log(`   Output: ${outputPath}`);

      // Create props object
      const props = {
        quote,
        author,
        backgroundColor: '#0a0a0a',
      };

      // Write props to temporary JSON file
      const propsPath = path.join(propsDir, `props-${i + 1}.json`);
      await writeFile(propsPath, JSON.stringify(props, null, 2));

      // Execute render command using file-based props
      const command = `npx remotion render src/index.tsx ShayariVideo "${outputPath}" --props="${propsPath}"`;

      await new Promise((resolve, reject) => {
        exec(command, { cwd: projectRoot }, (error, stdout, stderr) => {
          if (stdout) process.stdout.write(stdout);
          if (stderr) process.stderr.write(stderr);

          if (error) {
            console.error(`\n❌ Failed to render shayari ${i + 1}:`, error.message);
            reject(error);
          } else {
            console.log(`✅ Completed shayari ${i + 1}\n`);
            resolve();
          }
        });
      });

      // Clean up props file
      try {
        await exec(`del "${propsPath}" 2>nul`);
      } catch {
        // Ignore cleanup errors
      }
    }

    // Clean up temp directory if empty
    try {
      const files = await readdir(propsDir);
      if (files.length === 0) {
        await exec(`rmdir "${propsDir}" 2>nul || true`);
      }
    } catch {
      // Ignore cleanup errors
    }

    console.log('\n🎉 All videos rendered successfully!');
    console.log(`📁 Output directory: ${outDir}\n`);
    console.log('Generated files:');
    try {
      const { stdout } = await exec(`dir /b "${outDir}"`);
      console.log(stdout);
    } catch {
      // Ignore errors listing directory
    }

  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

renderShayariVideos();
