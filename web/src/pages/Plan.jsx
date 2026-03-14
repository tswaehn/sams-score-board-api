import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../api/mockApi.js";

export default function Plan() {
  const [stages, setStages] = useState([]);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeStageId, setActiveStageId] = useState(null);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchJson("/api/plan"), fetchJson("/api/teams")])
      .then(([planData, teamData]) => {
        if (isMounted) {
          setStages(planData.stages);
          setTeams(teamData.teams);
          setActiveStageId(planData.stages[0]?.id ?? null);
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

  const teamById = useMemo(() => {
    const map = new Map();
    teams.forEach((team) => {
      map.set(team.uuid, team);
    });
    return map;
  }, [teams]);

  return (
    <section className="page">
      <div className="page-header">
        <h1>Plan</h1>
        <p>Stages and group standings.</p>
      </div>
      {loading && <p className="muted">Loading plan...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <div className="stage-tabs">
          <div className="tab-list" role="tablist" aria-label="Stages">
            {stages.map((stage) => (
              <button
                key={stage.id}
                type="button"
                role="tab"
                aria-selected={activeStageId === stage.id}
                className={
                  activeStageId === stage.id ? "tab tab-active" : "tab"
                }
                onClick={() => setActiveStageId(stage.id)}
              >
                {stage.name}
              </button>
            ))}
          </div>
          {stages
            .filter((stage) => stage.id === activeStageId)
            .map((stage) => (
              <section key={stage.id} className="stage-card">
                <h2>{stage.name}</h2>
                {stage.groups && (
                  <div className="group-grid">
                    {stage.groups.map((group) => (
                      <div key={group.id} className="group-card">
                        <div className="group-title">Group {group.name}</div>
                        <div className="group-table">
                          <div className="group-header">
                            <span>Team</span>
                            <span>Spiele</span>
                            <span>S/N</span>
                            <span>Sätze</span>
                            <span>Bälle</span>
                            <span>Punkte</span>
                          </div>
                          {group.teams.map((team) => {
                            const meta = teamById.get(team.uuid);
                            return (
                              <div key={team.uuid} className="group-row">
                                <span className="team-cell">
                                  {meta && (
                                    <img
                                      className="group-logo"
                                      src={meta.logo_url}
                                      alt={`${meta.name} logo`}
                                    />
                                  )}
                                  <span>
                                    <div className="team-name">
                                      {meta ? meta.name : "Unknown team"}
                                    </div>
                                  </span>
                                </span>
                                <span>{team.played}</span>
                                <span>
                                  {team.wins}/{team.lost}
                                </span>
                                <span>
                                  {team.sets_won}:{team.sets_lost}
                                </span>
                                <span>
                                  {team.ball_points_won}:{team.ball_points_lost}
                                </span>
                                <span>{team.points}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {stage.matches && (
                  <div className="match-list">
                    {stage.matches.map((match) => {
                      const home = teamById.get(match.home_uuid);
                      const away = teamById.get(match.away_uuid);
                      return (
                        <div key={match.id} className="match-row">
                          <div className="match-team">
                            {home && (
                              <img
                                className="match-logo"
                                src={home.logo_url}
                                alt={`${home.name} logo`}
                              />
                            )}
                            <span>{home ? home.name : "Unknown team"}</span>
                          </div>
                          <div className="match-score">
                            {match.sets_home}:{match.sets_away}
                          </div>
                          <div className="match-team match-team-right">
                            <span>{away ? away.name : "Unknown team"}</span>
                            {away && (
                              <img
                                className="match-logo"
                                src={away.logo_url}
                                alt={`${away.name} logo`}
                              />
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            ))}
        </div>
      )}
    </section>
  );
}
