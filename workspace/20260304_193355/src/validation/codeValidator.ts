import fs from 'fs';

interface ValidationResult {
  isValid: boolean;
  issues: string[];
}

export const validateServerAction = (filePath: string): ValidationResult => {
  const content = fs.readFileSync(filePath, 'utf8');
  const issues: string[] = [];
  if (!content.includes('"use server"')) {
    issues.push('Missing "use server" directive in Server Action file.');
  }
  return { isValid: issues.length === 0, issues };
};

export const validateFetchCache = (filePath: string): ValidationResult => {
  const content = fs.readFileSync(filePath, 'utf8');
  const issues: string[] = [];
  if (content.includes('fetch') && !content.includes('next: { tags:')) {
    issues.push('Fetch call missing cache tags for ISR/revalidation.');
  }
  return { isValid: issues.length === 0, issues };
};

export const validateNextImage = (filePath: string): ValidationResult => {
  const content = fs.readFileSync(filePath, 'utf8');
  const issues: string[] = [];
  if (content.includes('<img') && !content.includes('next/image')) {
    issues.push('Found native <img> tag; use next/image for optimization on low-resource hardware.');
  }
  return { isValid: issues.length === 0, issues };
};
