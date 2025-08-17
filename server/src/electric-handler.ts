import type { Request, Response } from 'express'
import { Schema } from '@livestore/livestore'
import { ApiSchema, makeElectricUrl } from '@livestore/sync-electric'
import { makeDb } from './db.js'

const electricHost = process.env.ELECTRIC_HOST || 'http://localhost:30000'
const apiSecret = process.env.ELECTRIC_API_SECRET || 'change-me-electric-secret'
const authToken = process.env.AUTH_TOKEN || 'insecure-token-change-me'

export async function handleElectricAPI(req: Request, res: Response) {
  const url = new URL(req.url, `http://${req.headers.host}`)
  
  console.log('[Electric API] Request:', req.method, req.url)
  
  if (req.method === 'GET' || req.method === 'HEAD') {
    try {
      const searchParams = url.searchParams
      
      // For HEAD requests without parameters, return basic headers
      if (req.method === 'HEAD' && searchParams.toString() === '') {
        res.status(200)
        res.setHeader('content-type', 'application/octet-stream')
        res.end()
        return
      }
      
      const { url: electricUrl, storeId, needsInit, payload } = makeElectricUrl({
        electricHost,
        searchParams,
        apiSecret,
      })
      
      console.log('[Electric API] storeId:', storeId, 'needsInit:', needsInit)

      if ((payload as any)?.authToken !== authToken) {
        res.status(401).json({ error: 'Invalid auth token' })
        return
      }

      if (needsInit) {
        console.log('[Electric API] Running migration for storeId:', storeId)
        try {
          const db = makeDb(storeId)
          await db.migrate()
          await db.disconnect()
          console.log('[Electric API] Migration completed successfully')
        } catch (error) {
          console.error('[Electric API] Migration failed:', error)
          res.status(500).json({ error: 'Migration failed', details: error.message })
          return
        }
      }

      console.log('[Electric API] Fetching from Electric:', electricUrl)
      console.log('[Electric API] Payload passed to makeElectricUrl:', payload)
      const response = await fetch(electricUrl)
      
      console.log('[Electric API] Electric response status:', response.status)
      console.log('[Electric API] Electric headers:', Object.fromEntries(response.headers.entries()))
      
      let data: ArrayBuffer
      if (response.status >= 400) {
        const errorText = await response.text()
        console.log('[Electric API] Electric error response:', errorText)
        data = new TextEncoder().encode(errorText).buffer
      } else {
        data = await response.arrayBuffer()
      }
      
      res.status(response.status)
      
      // Wichtig: Electric Headers explizit durchreichen
      const electricHandle = response.headers.get('electric-handle')
      const electricOffset = response.headers.get('electric-offset')
      
      if (electricHandle) res.setHeader('electric-handle', electricHandle)
      if (electricOffset) res.setHeader('electric-offset', electricOffset)
      
      // Weitere wichtige Headers
      const contentType = response.headers.get('content-type')
      if (contentType) res.setHeader('content-type', contentType)
      
      console.log('[Electric API] Response headers set:', { electricHandle, electricOffset })
      
      // For HEAD requests, don't send the body
      if (req.method === 'HEAD') {
        res.end()
      } else {
        res.end(Buffer.from(data))
      }
    } catch (error) {
      console.error('[Electric API] Error:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  } else if (req.method === 'POST') {
    try {
      const parsedPayload = Schema.decodeUnknownSync(ApiSchema.PushPayload)(req.body)

      const db = makeDb(parsedPayload.storeId)
      await db.createEvents(parsedPayload.batch)
      await db.disconnect()

      res.status(200).json({ success: true })
    } catch (error) {
      console.error('[Electric API] Error processing POST:', error)
      res.status(500).json({ error: 'Internal server error' })
    }
  } else {
    res.status(405).send('Method not allowed')
  }
}