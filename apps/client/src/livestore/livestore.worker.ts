import { makeWorker } from '@livestore/adapter-web/worker'
import { makeCfSync } from '@livestore/sync-cf'
import { schema } from './schema'

const url = 'ws://localhost:8000'

makeWorker({
  schema,
  sync: { backend: makeCfSync({ url }) },
})