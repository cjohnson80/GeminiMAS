import fs from 'fs';
import path from 'path';

const dirs = ['app', 'components', 'lib', 'hooks', 'types'];
const baseDir = '/home/chrisj/gemini_agents/workspace/20260304_193355';

export const scaffold = () => {
  dirs.forEach(dir => {
    const p = path.join(baseDir, dir);
    if (!fs.existsSync(p)) fs.mkdirSync(p);
    console.log(`Created: ${dir}`);
  });

  const pkg = {
    name: "gemini-mas-project",
    version: "1.0.0",
    dependencies: { "next": "latest", "react": "latest", "react-dom": "latest" }
  };
  fs.writeFileSync(path.join(baseDir, 'package.json'), JSON.stringify(pkg, null, 2));
  console.log("Initialized package.json");
};

scaffold();
