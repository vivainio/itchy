// Reserve stdout for JSON; Scratch diagnostics go to stderr.
console.log = (...args) => console.error(...args);
const { loadVM } = await import('./runtime.js');
const input = await Bun.stdin.json();
const run = await loadVM(Buffer.from(input.project, 'base64'));
const snapshots = [];
try {
  for (const step of input.steps) {
    switch (step.op) {
      case 'flag': run.flag(); break;
      case 'tick': run.tick(step.count); break;
      case 'key': run.key(step.key, step.down); break;
      case 'snapshot':
        snapshots.push({
          sprites: Object.fromEntries(step.sprites.map(name => {
            const target = run.sprite(name);
            return [name, { x: target.x, y: target.y }];
          })),
          variables: Object.fromEntries(step.variables.map(name => [name, run.variable(name)])),
        });
        break;
      default: throw new Error(`Unknown scenario operation: ${step.op}`);
    }
  }
  process.stdout.write(JSON.stringify(snapshots));
} finally { run.close(); }
