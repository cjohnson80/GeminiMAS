import { validateServerAction, validateFetchCache, validateNextImage } from './src/utils/codeValidator';

const testAction = '"use server"; export async function test() {}';
const testFetch = 'fetch("/api", { next: { tags: ["test"] } })';
const testImg = 'import Image from "next/image"; <Image src="" width={100} height={100} />';

console.log("Server Action Valid:", validateServerAction(testAction));
console.log("Fetch Cache Valid:", validateFetchCache(testFetch));
console.log("Next Image Valid:", validateNextImage(testImg));
