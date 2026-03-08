function Settings({ settings, onChange }) {
  const update = (key, value) => {
    onChange({ ...settings, [key]: value })
  }

  return (
    <div className="settings">
      <label>
        Results:
        <select
          value={settings.top_n}
          onChange={(e) => update('top_n', Number(e.target.value))}
        >
          {[1, 2, 3, 5, 10].map((n) => (
            <option key={n} value={n}>{n}</option>
          ))}
        </select>
      </label>

      <label>
        Tab type:
        <select
          value={settings.tab_type}
          onChange={(e) => update('tab_type', e.target.value)}
        >
          <option value="any">All</option>
          <option value="图片谱">图片谱 (Image)</option>
          <option value="GTP谱">GTP谱 (Guitar Pro)</option>
          <option value="PDF谱">PDF谱</option>
          <option value="和弦谱">和弦谱 (Chords)</option>
        </select>
      </label>

      <label>
        Style:
        <select
          value={settings.style}
          onChange={(e) => update('style', e.target.value)}
        >
          <option value="any">All</option>
          <option value="弹唱">弹唱 (Strum & Sing)</option>
          <option value="指弹">指弹 (Fingerstyle)</option>
          <option value="独奏">独奏 (Solo)</option>
        </select>
      </label>
    </div>
  )
}

export default Settings
