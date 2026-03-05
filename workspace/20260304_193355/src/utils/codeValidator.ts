import fs from 'fs';

export const validateNextJsImplementation = (filePath: string): { serverAction: boolean, fetchCache: boolean, nextImage: boolean } => {
  const content = fs.readFileSync(filePath, 'utf8');
  
  return {
    serverAction: content.includes('"use server"'),
    fetchCache: content.includes('next: { tags:'),
    nextImage: content.includes('import Image from "next/image"') || content.includes('from "next/image"')
  };
};

// Basic test execution for the validator
const results = validateNextJsImplementation(process.argv[2]);
console.log(JSON.stringify(results));
