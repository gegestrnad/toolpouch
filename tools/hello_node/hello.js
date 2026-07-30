// Hello-world test tool for the Node.js runtime.
// Spec §6 Phase 6 checkpoint: test arg-with-spaces passing.

function parseArgs(argv) {
    const params = {};
    for (let i = 2; i < argv.length; i += 2) {
        const key = argv[i].replace(/^--/, '');
        params[key] = argv[i + 1] || '';
    }
    return params;
}

const args = parseArgs(process.argv);

if (!args.path) {
    console.error('[ERROR] No --path specified');
    process.exit(1);
}

console.log('PROGRESS:0');
console.log(`[OK] Hello from Node ${process.version}`);
console.log(`[OK] path_arg:   ${args.path}`);
console.log('PROGRESS:50');

if (args.path.includes(' ')) {
    console.log('[OK] Path contains spaces - preserved correctly.');
} else {
    console.log('[WARN] Path has no spaces - try a path with spaces to really test.');
}

console.log('PROGRESS:100');
console.log('[OK] Done.');
