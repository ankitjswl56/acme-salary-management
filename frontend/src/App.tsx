import { useEffect, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface HealthResponse {
  status: string
}

function App() {
  const [status, setStatus] = useState('checking...')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json() as Promise<HealthResponse>)
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('unreachable'))
  }, [])

  return (
    <section id="center">
      <h1>ACME Salary Management</h1>
      <p>
        Backend status: <strong>{status}</strong>
      </p>
    </section>
  )
}

export default App
