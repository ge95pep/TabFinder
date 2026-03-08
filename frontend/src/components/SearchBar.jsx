import { useState } from 'react'

function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSearch(query)
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter song name... e.g. 晴天"
        disabled={loading}
        autoFocus
      />
      <button type="submit" disabled={loading || !query.trim()}>
        {loading ? '⏳' : '🔍 Search'}
      </button>
    </form>
  )
}

export default SearchBar
