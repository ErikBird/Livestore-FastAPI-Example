import { Schema } from '@livestore/livestore'
import { ApiSchema, makeElectricUrl } from '@livestore/sync-electric'

const electricHost = 'http://localhost:30000'

export async function handleElectricRequest(url: string, method: string, body?: any) {
  console.log('[Electric Handler] Request:', method, url)
  
  if (method === 'GET') {
    try {
      const urlObj = new URL(url, window.location.origin)
      const searchParams = urlObj.searchParams
      
      const { url: electricUrl, storeId, needsInit, payload } = makeElectricUrl({
        electricHost,
        searchParams,
        apiSecret: 'change-me-electric-secret',
      })
      
      console.log('[Electric Handler] storeId:', storeId, 'needsInit:', needsInit)

      if ((payload as any)?.authToken !== 'insecure-token-change-me') {
        return {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ error: 'Invalid auth token' })
        }
      }

      if (needsInit) {
        console.log('[Electric Handler] Migration needed for storeId:', storeId)
        // TODO: Handle migration in the browser context if needed
        console.warn('[Electric Handler] Migration not implemented in browser context')
      }

      console.log('[Electric Handler] Fetching from Electric:', electricUrl)
      const response = await fetch(electricUrl)
      const data = await response.arrayBuffer()
      
      console.log('[Electric Handler] Electric response status:', response.status)
      console.log('[Electric Handler] Electric headers:', Object.fromEntries(response.headers.entries()))
      
      // Wichtig: Electric Headers sammeln
      const headers: Record<string, string> = {}
      const electricHandle = response.headers.get('electric-handle')
      const electricOffset = response.headers.get('electric-offset')
      const contentType = response.headers.get('content-type')
      
      if (electricHandle) headers['electric-handle'] = electricHandle
      if (electricOffset) headers['electric-offset'] = electricOffset
      if (contentType) headers['content-type'] = contentType
      
      console.log('[Electric Handler] Response headers:', headers)
      
      return {
        status: response.status,
        headers,
        body: data
      }
    } catch (error) {
      console.error('[Electric Handler] Error:', error)
      return {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Internal error' })
      }
    }
  } else if (method === 'POST') {
    try {
      const parsedPayload = Schema.decodeUnknownSync(ApiSchema.PushPayload)(body)
      
      // In der Browser-Umgebung können wir die Events nicht direkt in eine DB schreiben
      // Stattdessen müssten wir sie an Electric weiterleiten oder im IndexedDB speichern
      console.log('[Electric Handler] Push payload received:', parsedPayload)
      
      // TODO: Implement browser-side event handling
      console.warn('[Electric Handler] Push not fully implemented in browser context')
      
      return {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ success: true })
      }
    } catch (error) {
      console.error('[Electric Handler] Error processing POST:', error)
      return {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: 'Internal error' })
      }
    }
  } else {
    return {
      status: 405,
      headers: {},
      body: 'Method not allowed'
    }
  }
}