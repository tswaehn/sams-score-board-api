import { Box, Button, FormControl, InputLabel, MenuItem, Select } from "@mui/material";

export default function CompetitionMatchGroups({ groups, selectedUuid, onSelect }) {
  return <>
    <FormControl fullWidth sx={{ display: { xs: "block", sm: "none" } }}>
      <InputLabel id="match-group-label">Match group</InputLabel>
      <Select labelId="match-group-label" label="Match group" value={selectedUuid} onChange={(event) => onSelect(event.target.value)}>
        {groups.map((group) => <MenuItem key={group.uuid} value={group.uuid}>{group.name || "Match group"}</MenuItem>)}
      </Select>
    </FormControl>
    <Box sx={{ display: { xs: "none", sm: "flex" }, flexWrap: "wrap", gap: 1 }}>
      {groups.map((group) => <Button key={group.uuid} variant={group.uuid === selectedUuid ? "contained" : "outlined"} onClick={() => onSelect(group.uuid)}>{group.name || "Match group"}</Button>)}
    </Box>
  </>;
}
