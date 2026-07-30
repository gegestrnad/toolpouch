// JSON Validator - Validate JSON files and report detailed errors
const fs = require('fs');
const path = require('path');

// Parse arguments (--param_id value format)
function parseArgs(args) {
    const params = {};
    for (let i = 2; i < args.length; i += 2) {
        const key = args[i].replace(/^--/, '');
        params[key] = args[i + 1] || '';
    }
    return params;
}

function progress(pct) {
    console.log(`PROGRESS:${pct}`);
}

const args = parseArgs(process.argv);

if (!args.file) {
    console.error('[ERROR] No file specified');
    process.exit(1);
}

const filePath = args.file;

if (!fs.existsSync(filePath)) {
    console.error(`[ERROR] File not found: ${filePath}`);
    process.exit(1);
}

progress(10);

try {
    const content = fs.readFileSync(filePath, 'utf-8');
    progress(40);

    console.log(`[OK] Reading ${path.basename(filePath)} (${content.length} chars)`);

    progress(60);

    const parsed = JSON.parse(content);

    progress(90);

    // Report structure
    const type = Array.isArray(parsed) ? 'Array' : typeof parsed;
    let summary = '';

    if (Array.isArray(parsed)) {
        summary = `Array with ${parsed.length} elements`;
    } else if (typeof parsed === 'object' && parsed !== null) {
        const keys = Object.keys(parsed);
        summary = `Object with ${keys.length} keys: ${keys.slice(0, 5).join(', ')}${keys.length > 5 ? '...' : ''}`;
    } else {
        summary = `Value: ${String(parsed).substring(0, 50)}`;
    }

    console.log(`[OK] Valid JSON (${type})`);
    console.log(`  ${summary}`);

    progress(100);

} catch (e) {
    progress(90);

    if (e instanceof SyntaxError) {
        console.error(`[ERROR] Invalid JSON: ${e.message}`);

        // Try to extract line/column info
        const match = e.message.match(/position (\d+)/);
        if (match) {
            const pos = parseInt(match[1]);
            const lines = content.substring(0, pos).split('\n');
            console.error(`  Near line ${lines.length}, column ${lines[lines.length - 1].length}`);
        }
    } else {
        console.error(`[ERROR] ${e.message}`);
    }

    progress(100);
    process.exit(1);
}
