function TabCard({ tab }) {
  const stars = (rating) => {
    if (rating === null || rating === undefined) return '—'
    const full = Math.round(rating)
    return '★'.repeat(full) + '☆'.repeat(5 - full)
  }

  const formatViews = (n) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
    return String(n)
  }

  const rankEmoji = ['🥇', '🥈', '🥉']
  const badge = rankEmoji[tab.rank - 1] || `#${tab.rank}`

  return (
    <a
      className="tab-card"
      href={tab.url}
      target="_blank"
      rel="noreferrer"
    >
      <div className="tab-rank">
        <span className="rank-badge">{badge}</span>
        <span className="score">{tab.score}</span>
      </div>

      <div className="tab-info">
        <div className="tab-title">{tab.title}</div>
        <div className="tab-artist">{tab.artist}</div>

        <div className="tab-meta">
          <span className="tab-type">{tab.tab_type}</span>
          {tab.tags.map((tag) => (
            <span key={tag} className="tab-tag">{tag}</span>
          ))}
        </div>

        <div className="tab-stats">
          <span title="Accuracy">🎯 {stars(tab.accuracy_rating)}</span>
          <span title="Difficulty">💪 {stars(tab.difficulty_rating)}</span>
          <span title="Views">👁 {formatViews(tab.views)}</span>
          <span title="Ratings">📊 {tab.num_ratings} ratings</span>
        </div>

        <div className="tab-uploader">
          Uploaded by: {tab.uploader}
        </div>
      </div>

      <div className="tab-score-breakdown">
        <ScoreBar label="Accuracy" value={tab.score_breakdown.accuracy} />
        <ScoreBar label="Views" value={tab.score_breakdown.views} />
        <ScoreBar label="Complete" value={tab.score_breakdown.completeness} />
        <ScoreBar label="Type" value={tab.score_breakdown.type_match} />
        <ScoreBar label="Rated" value={tab.score_breakdown.recency} />
      </div>
    </a>
  )
}

function ScoreBar({ label, value }) {
  return (
    <div className="score-bar">
      <span className="score-label">{label}</span>
      <div className="score-track">
        <div
          className="score-fill"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
      <span className="score-value">{Math.round(value)}</span>
    </div>
  )
}

export default TabCard
