import { useState } from 'react'
import SearchBar from './components/SearchBar'
import Results from './components/Results'
import Settings from './components/Settings'
import './App.css'

const API_BASE = 'http://localhost:8888'

function App() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState({
    top_n: 3,
    tab_type: 'any',
    style: 'any',
    source: 'all',
  })

  const handleSearch = async (song) => {
    if (!song.trim()) return

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const params = new URLSearchParams({
        song: song.trim(),
        top_n: settings.top_n,
        tab_type: settings.tab_type,
        style: settings.style,
        source: settings.source,
      })

      const resp = await fetch(`${API_BASE}/api/search?${params}`)
      if (!resp.ok) throw new Error(`Search failed (${resp.status})`)

      const data = await resp.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🎸 TabFinder</h1>
        <p className="subtitle">Find the best guitar tabs, fast.</p>
      </header>

      <main className="main">
        <SearchBar onSearch={handleSearch} loading={loading} />
        <Settings settings={settings} onChange={setSettings} />

        {loading && <div className="loading">🔍 Searching tabs...</div>}
        {error && <div className="error">❌ {error}</div>}
        {results && <Results data={results} />}
      </main>

      <footer className="footer">
        <p>Tabs sourced from <a href="https://www.jitashe.org" target="_blank" rel="noreferrer">jitashe.org</a></p>
      </footer>
    </div>
  )
}

export default App
