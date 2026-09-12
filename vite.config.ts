import { cp, readFile } from 'node:fs/promises'
import { isAbsolute, relative, resolve, sep } from 'node:path'
import { defineConfig, type Plugin, type ResolvedConfig } from 'vite'
import react from '@vitejs/plugin-react'

function roomCatalog(): Plugin {
  const publicId = 'virtual:room-catalog'
  const resolvedId = '\0' + publicId
  let registryPath: string
  return {
    name: 'room-catalog',
    configResolved(config) {
      registryPath = resolve(config.root, 'src/data/registry.json')
    },
    resolveId(id) {
      if (id === publicId) return resolvedId
    },
    async load(id) {
      if (id !== resolvedId) return
      this.addWatchFile(registryPath)
      const registry = JSON.parse(await readFile(registryPath, 'utf8')) as {
        rooms: Array<{ seats: unknown[]; [key: string]: unknown }>
      }
      // Derive public browsing metadata from the one authoritative registry.
      // Detailed coordinates are imported only by the room and editor routes.
      const rooms = registry.rooms.map(({ seats, ...room }) => ({ ...room, seatCount: seats.length }))
      return `export default ${JSON.stringify({ rooms })}`
    },
    handleHotUpdate(context) {
      if (context.file !== registryPath) return
      const catalog = context.server.moduleGraph.getModuleById(resolvedId)
      if (catalog) {
        context.server.moduleGraph.invalidateModule(catalog)
        return [...context.modules, catalog]
      }
    },
  }
}

function publicRuntimeAssets(): Plugin {
  let config: ResolvedConfig
  return {
    name: 'public-runtime-assets',
    apply: 'build',
    configResolved(resolved) { config = resolved },
    async writeBundle() {
      if (!config.publicDir) return
      const output = resolve(config.root, config.build.outDir)
      const destination = relative(config.root, output)
      if (!destination || destination.startsWith('..') || isAbsolute(destination) || output === config.publicDir) {
        throw new Error('Build output must be a separate directory inside the project')
      }
      // Preserve all source files and original public floor-plan URLs. Only
      // diagnostic overlays are omitted from deployment; dev still serves them.
      await cp(config.publicDir, output, {
        recursive: true,
        filter: (source) => {
          const parts = relative(config.publicDir, source).split(sep)
          return !(parts[0] === 'maps' && parts[1] === 'debug')
        },
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), roomCatalog(), publicRuntimeAssets()],
  build: { copyPublicDir: false },
})
