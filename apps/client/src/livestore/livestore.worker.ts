import { makeWorker } from '@livestore/adapter-web/worker'
import { makeCfSync } from '@livestore/sync-cf'
import { schema } from './schema'

// Use WebSocket URL from environment or default to proxy route
// In production, this will be ws://localhost:3000/websocket through Caddy
const url = import.meta.env.VITE_WS_URL || 'ws://localhost:3000/websocket'

makeWorker({
  schema,
  sync: { backend: makeCfSync({ url }) },
})