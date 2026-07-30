// JSON Sorter - Sorts JSON object keys alphabetically and pretty-prints.
// Demonstrates: .js tool with file/save/dropdown parameters, Node.js runtime,
// and the stdout protocol ([OK]/[WARN]/[ERROR] + PROGRESS:N).

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
    const params = {};
    for (let i = 2; i < argv.length; i += 2) {
        const key = argv[i].replace(/^--/, '');
        params[key] = argv[i + 1] || '';
    }
    return params;
}

function sortKeys(obj) {
    if (Array.isArray(obj)) {
        return obj.map(sortKeys);
    }
    if (obj !== null && typeof obj === 'object') {
        const sorted = {};
        for (const key of Object.keys(obj).sort()) {
            sorted[key] = sortKeys(obj[key]);
        }
        return sorted;
    }
    return obj;
}

const args = parseArgs(process.argv);

if (!args.input_file) {
    console.error('[ERROR] No --input_file specified');
    process.exit(1);
}

const inputPath = args.input_file;
const outputPath = args.output_file && args.output_file.trim() ? args.output_file.trim() : inputPath;

// Determine indent
let indent;
if (args.indent === 'tab') {
    indent = '\t';
} else {
    indent = parseInt(args.indent) || 2;
}

console.log('PROGRESS:10');

if (!fs.existsSync(inputPath)) {
    console.error(`[ERROR] File not found: ${inputPath}`);
    process.exit(1);
}

console.log(`[OK] Reading ${path.basename(inputPath)}`);
const content = fs.readFileSync(inputPath, 'utf-8');
console.log('PROGRESS:30');

let data;
try {
    data = JSON.parse(content);
    console.log('[OK] Valid JSON parsed');
} catch (e) {
    console.error(`[ERROR] Invalid JSON: ${e.message}`);
    process.exit(1);
}

console.log('PROGRESS:50');
console.log('[OK] Sorting keys recursively...');

const sorted = sortKeys(data);

console.log('PROGRESS:70');

const output = JSON.stringify(sorted, null, indent) + '\n';
fs.writeFileSync(outputPath, output, 'utf-8');

console.log('PROGRESS:100');
console.log(`[OK] Sorted JSON written to: ${path.basename(outputPath)}`);
console.log(`[OK] Output size: ${output.length} chars`);
