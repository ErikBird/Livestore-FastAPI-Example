import type { IncomingMessage, ServerResponse } from 'http'
import { Schema } from '@livestore/livestore'
import { ApiSchema, makeElectricUrl } from '@livestore/sync-electric'
import { makeDb } from '../server/db'

const electricHost = 'http://localhost:30000'

export async function handleElectricAPI(req: IncomingMessage, res: ServerResponse) {
  const url = new URL(req.url!, `http://${req.headers.host}`)
  
  console.log('[Electric API] Request:', req.method, req.url)
  
  if (req.method === 'GET') {
    try {
      const searchParams = url.searchParams
      const { url: electricUrl, storeId, needsInit, payload } = makeElectricUrl({
        electricHost,
        searchParams,
        apiSecret: 'change-me-electric-secret',
      })
      
      console.log('[Electric API] storeId:', storeId, 'needsInit:', needsInit)

      if ((payload as any)?.authToken !== 'insecure-token-change-me') {
        res.statusCode = 401
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ error: 'Invalid auth token' }))
        return
      }

      if (needsInit) {
        console.log('[Electric API] Running migration for storeId:', storeId)
        const db = makeDb(storeId)
        await db.migrate()
        await db.disconnect()
        console.log('[Electric API] Migration completed')
      }

      console.log('[Electric API] Fetching from Electric:', electricUrl)
      const response = await fetch(electricUrl)
      const data = await response.arrayBuffer()
      
      console.log('[Electric API] Electric response status:', response.status)
      console.log('[Electric API] Electric headers:', Object.fromEntries(response.headers.entries()))
      
      res.statusCode = response.status
      
      // Wichtig: Electric Headers explizit durchreichen
      const electricHandle = response.headers.get('electric-handle')
      const electricOffset = response.headers.get('electric-offset')
      
      if (electricHandle) res.setHeader('electric-handle', electricHandle)
      if (electricOffset) res.setHeader('electric-offset', electricOffset)
      
      // Weitere wichtige Headers
      const contentType = response.headers.get('content-type')
      if (contentType) res.setHeader('content-type', contentType)
      
      console.log('[Electric API] Response headers set:', { electricHandle, electricOffset })
      
      res.end(Buffer.from(data))
    } catch (error) {
      res.statusCode = 500
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify({ error: 'Internal server error' }))
    }
  } else if (req.method === 'POST') {
    let body = ''
    
    req.on('data', chunk => {
      body += chunk.toString()
    })
    
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body)
        const parsedPayload = Schema.decodeUnknownSync(ApiSchema.PushPayload)(payload)

        const db = makeDb(parsedPayload.storeId)
        await db.createEvents(parsedPayload.batch)
        await db.disconnect()

        res.statusCode = 200
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ success: true }))
      } catch (error) {
        res.statusCode = 500
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ error: 'Internal server error' }))
      }
    })
  } else {
    res.statusCode = 405
    res.end('Method not allowed')
  }
}