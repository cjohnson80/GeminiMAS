import * as fs from 'fs';

export const validateNextJsPatterns = (filePath: string) => {
  const content = fs.readFileSync(filePath, 'utf8');
  const errors: string[] = [];

  // Check for Server Actions
  if (content.includes('"use server"') || content.includes("'use server'")) {
    console.log(`[Validator] Found Server Action in ${filePath}`);
  }

  // Check for fetch with cache tags
  const fetchRegex = /fetch\([^)]*\)/g;
  if (fetchRegex.test(content) && !content.includes('next: { tags:')) {
    errors.push(`Missing cache tags in fetch call within ${filePath}`);
  }

  // Check for next/image usage
  if (content.includes('import Image from "next/image"') && !content.includes('sizes=')) {
    errors.push(`Missing 'sizes' prop on next/image in ${filePath}`);
  }

  return errors;
};
