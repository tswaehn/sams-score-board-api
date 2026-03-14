import { useEffect, useState } from "react";
import { fetchJson } from "../api/mockApi.js";

export default function Live() {
  const [match, setMatch] = useState(null);
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/live")
      .then((data) => {
        if (isMounted) {
          setMatch(data.match);
          setStats(data.stats);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <h1>Live</h1>
        <p>Live scoreboard feed and momentum tracker.</p>
      </div>
      {loading && <p className="muted">Loading live feed...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && match && (
        <>
          <div className="live-card">
            <div>
              <div className="live-label">Current Match</div>
              <div className="live-match">
                {match.home} vs {match.away}
              </div>
            </div>
            <div className="score">
              <span>{match.score.home}</span>
              <span className="score-divider">:</span>
              <span>{match.score.away}</span>
            </div>
          </div>
          <div className="stat-grid">
            {stats.map((stat) => (
              <div key={stat.id} className="stat">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
