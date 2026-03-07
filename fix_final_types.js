const fs = require('fs');

function replaceInFile(filePath, replacements) {
  if (!fs.existsSync(filePath)) return;
  let content = fs.readFileSync(filePath, 'utf8');
  let original = content;
  for (const [search, replace] of replacements) {
    content = content.replace(search, replace);
  }
  if (content !== original) {
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`Fixed ${filePath}`);
  }
}

// 1. Infrastructure API
replaceInFile('workspace/goldeneye/src/app/api/infrastructure/route.ts', [
  [/(element|item|node|way): any/g, '$1: Record<string, unknown>'],
  [/error: any/g, 'error: unknown']
]);

// 2. Intercept API
replaceInFile('workspace/goldeneye/src/app/api/intercept/route.ts', [
  [/(element|item|node|way|freq): any/g, '$1: Record<string, unknown>'],
  [/error: any/g, 'error: unknown']
]);

// 3. Seismic API
replaceInFile('workspace/goldeneye/src/app/api/seismic/route.ts', [
  [/(element|item|node|way|feature): any/g, '$1: Record<string, unknown>'],
  [/error: any/g, 'error: unknown']
]);

// 4. Webcams API
replaceInFile('workspace/goldeneye/src/app/api/webcams/route.ts', [
  [/(element|item|node|way|cam): any/g, '$1: Record<string, unknown>'],
  [/catch \(error\) \{/g, 'catch (_error) {'],
  [/error: any/g, 'error: unknown']
]);

// 5. DashboardShell
replaceInFile('workspace/goldeneye/src/components/layout/DashboardShell.tsx', [
  [/: any/g, ': Record<string, unknown>'],
  [/error: any/g, 'error: unknown']
]);

// 6. Map
replaceInFile('workspace/goldeneye/src/components/map/Map.tsx', [
  [/import \{([^}]*)Plane, Activity, Ship, Video, Radio([^}]*)\} from 'lucide-react';/g, 'import {$1$2} from \'lucide-react\';'],
  [/@ts-ignore/g, '@ts-expect-error'],
  [/catch \(_e\) \{/g, 'catch {']
]);

