import LeagueTable from "./LeagueTable.jsx";

export default function CompetitionTable({ rankingGroup }) {
  return <LeagueTable rankings={rankingGroup?.rankings || []} />;
}
