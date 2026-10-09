// Build in a short physical directory: Windows Ninja/Kotlin dislike drive aliases.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const source = path.resolve(__dirname, '..');
const target = fs.mkdtempSync(path.join(os.tmpdir(), 'tfx-'));
fs.cpSync(source, target, {
  recursive: true,
  filter(file) {
    const parts = path.relative(source, file).split(path.sep);
    if (['android', 'ios', 'cx', 'builds', '.expo', '.git', '.claude'].includes(parts[0])) return false;
    if (parts.includes('.cache')) return false;
    const android = parts.indexOf('android');
    if (parts.includes('node_modules') && android >= 0 && ['build', '.cxx', '.gradle'].includes(parts[android + 1])) return false;
    const gradle = parts.findIndex(p => p.endsWith('gradle-plugin'));
    if (gradle >= 0 && parts.slice(gradle + 1).some(p => ['build', '.gradle', '.kotlin'].includes(p))) return false;
    return true;
  }
});
fs.writeFileSync(path.join(target, '.traffix-native-snapshot'), source);
process.stdout.write(JSON.stringify({ path: target }));
