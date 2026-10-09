// Compile the actual TypeScript adapter in memory, without an Expo runtime.
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const ts = require("typescript");
function load(name, dependencies = {}) {
  const filename = path.resolve(__dirname, "../src", name + ".ts");
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const mod = new Module(filename, module);
  mod.paths = module.paths;
  const original = mod.require.bind(mod);
  mod.require = (id) => dependencies[id] || original(id);
  mod._compile(compiled, filename);
  return mod.exports;
}
module.exports = load("client", { "./protocol": load("protocol") });
