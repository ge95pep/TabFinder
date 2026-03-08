import TabCard from './TabCard'

function Results({ data }) {
  if (!data || data.top_tabs.length === 0) {
    return <div className="no-results">No tabs found. Try a different search?</div>
  }

  return (
    <div className="results">
      <div className="results-header">
        <span className="results-count">
          Found <strong>{data.results_found}</strong> tabs for "<strong>{data.song}</strong>"
        </span>
        <span className="results-source">via {data.source}</span>
      </div>

      <div className="tab-list">
        {data.top_tabs.map((tab) => (
          <TabCard key={tab.url} tab={tab} />
        ))}
      </div>
    </div>
  )
}

export default Results
