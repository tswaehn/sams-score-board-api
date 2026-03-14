import { useEffect, useState } from "react";
import { fetchJson } from "../api/mockApi.js";

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/teams")
      .then((data) => {
        if (isMounted) {
          setTeams(data.teams);
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
        <h1>Setzliste</h1>
      </div>
      {loading && <p className="muted">Loading teams...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <div className="team-list">
          {teams.map((team) => (
            <article key={team.uuid} className="team-row">
              <img
                className="team-logo"
                src={team.logo_url}
                alt={`${team.name} logo`}
              />
              <div className="team-meta">
                <p className="muted">{team.short_name}</p>
                <h2>{team.name}</h2>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
