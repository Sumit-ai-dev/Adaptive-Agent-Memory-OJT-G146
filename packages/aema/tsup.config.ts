import { defineConfig } from 'tsup';

export default defineConfig([
  // Core library (ESM + CJS + d.ts)
  {
    entry: {
      index: 'src/index.ts',
      mcp: 'src/mcp.ts',
    },
    format: ['esm', 'cjs'],
    dts: true,
    sourcemap: true,
    clean: true,
    shims: true,
  },
  // Executable binaries (preserving existing shebangs)
  {
    entry: {
      cli: 'src/cli.ts',
      mcp: 'src/mcp.ts',
    },
    format: ['esm'],
    outExtension() {
      return { js: '.js' };
    },
  },
]);
