import express from 'express'
import cors from 'cors'
import { handleElectricAPI } from './electric-handler.js'

const app = express()
const PORT = process.env.PORT || 3001

// Enable CORS for all origins in development
app.use(cors())

// Parse JSON bodies
app.use(express.json())

// Electric API endpoint
app.all('/api/electric', async (req, res) => {
  await handleElectricAPI(req, res)
})

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`[API Server] Running on http://localhost:${PORT}`)
  console.log(`[API Server] Electric endpoint: http://localhost:${PORT}/api/electric`)
})