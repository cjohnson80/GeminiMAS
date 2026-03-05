import { validateCode } from './src/utils/codeValidator';
import fs from 'fs';

const testFile = './test_component.tsx';
fs.writeFileSync(testFile, '"use server"; import Image from "next/image"; fetch("/", { next: { tags: ["test"] } });');

const result = validateCode(testFile);
console.log(`Server Action Valid: ${result.details.serverAction}`);
console.log(`Fetch Cache Valid: ${result.details.fetchCache}`);
console.log(`Next Image Valid: ${result.details.nextImage}`);
