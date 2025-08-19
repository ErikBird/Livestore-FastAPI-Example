<script setup lang="ts">
import { makePersistedAdapter } from '@livestore/adapter-web'
import LiveStoreSharedWorker from '@livestore/adapter-web/shared-worker?sharedworker'
import { LiveStoreProvider } from 'vue-livestore'
import ToDos from './components/to-dos.vue'
import LiveStoreWorker from './livestore/livestore.worker?worker'
import { schema } from './livestore/schema'

const adapter = makePersistedAdapter({
  storage: { type: 'opfs' },
  worker: LiveStoreWorker,
  sharedWorker: LiveStoreSharedWorker,
  resetPersistence: true, // WARNING: Resets database on every start - only for development!
})

const storeOptions = {
  schema,
  adapter,
  storeId: 'test_store',
  syncPayload: {
    authToken: 'insecure-token-change-me'
  }
}
</script>

<template>
  <LiveStoreProvider :options="storeOptions">
    <template #loading>
      <div class="min-h-screen flex items-center justify-center bg-gray-50">
        <div class="text-lg text-gray-600">Loading LiveStore...</div>
      </div>
    </template>
    <ToDos />
  </LiveStoreProvider>
</template>