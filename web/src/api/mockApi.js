const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const database = {
  "/api/teams": {
    teams: [
      {
        uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
        short_name: "ETV",
        name: "Eimsbütteler TV",
        logo_url: "https://placehold.co/120x120?text=ETV"
      },
      {
        uuid: "0e1a9b36-71d0-4b6d-9a44-2b6b5af5b0c2",
        short_name: "BTSC",
        name: "Berliner TSC",
        logo_url: "https://placehold.co/120x120?text=BTSC"
      },
      {
        uuid: "3d9b1f2c-9c2a-4f02-8dd5-5c8f0f2bcb3f",
        short_name: "LEV",
        name: "LE Volleys",
        logo_url: "https://placehold.co/120x120?text=LEV"
      },
      {
        uuid: "b8b2f14d-6d32-4f8a-8c87-9d8b2a5a9c11",
        short_name: "SCC",
        name: "SCC Juniors",
        logo_url: "https://placehold.co/120x120?text=SCC"
      },
      {
        uuid: "9e3f2d61-8f85-4c34-9b7d-0f6f3c62d1a9",
        short_name: "SCP",
        name: "SC Potsdam",
        logo_url: "https://placehold.co/120x120?text=SCP"
      },
      {
        uuid: "6c6b3d25-0f9a-4c62-9f4e-7a1f6f2e3b9a",
        short_name: "VSA",
        name: "VV Sachsen-Anhalt",
        logo_url: "https://placehold.co/120x120?text=VSA"
      },
      {
        uuid: "2f7a9c1d-6e54-4c1b-8b9a-3f2d6b1c7e5a",
        short_name: "LAB",
        name: "Landesauswahl Berlin",
        logo_url: "https://placehold.co/120x120?text=LAB"
      },
      {
        uuid: "4b1c7e2a-9d5f-4b2c-8c3f-1e7a5d2b9f4c",
        short_name: "VCD",
        name: "VC Dresden",
        logo_url: "https://placehold.co/120x120?text=VCD"
      },
      {
        uuid: "7a2b9c1e-5d6f-4c2a-8b3f-9e1a7c2d5f6b",
        short_name: "VHP",
        name: "VG Halstenbek-Pinneberg",
        logo_url: "https://placehold.co/120x120?text=VHP"
      },
      {
        uuid: "1f6b2c9a-4d7e-4b1c-8a3f-5c2d7e1b9f6a",
        short_name: "VYT",
        name: "Volleyball YoungStars Thüringen",
        logo_url: "https://placehold.co/120x120?text=VYT"
      },
      {
        uuid: "6a2f9c1e-4d7b-4a2c-8f3e-1b7c2d5f9a6b",
        short_name: "SSC",
        name: "SSC Karlsruhe",
        logo_url: "https://placehold.co/120x120?text=SSC"
      },
      {
        uuid: "3b7d2f9a-1c6e-4b2f-9a5c-7e2b1f6c9d4a",
        short_name: "SSU",
        name: "SSV Ulm 1846",
        logo_url: "https://placehold.co/120x120?text=SSU"
      },
      {
        uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
        short_name: "VCB",
        name: "VC Baustetten",
        logo_url: "https://placehold.co/120x120?text=VCB"
      },
      {
        uuid: "5d1b7c2a-9f6e-4b3c-8a2d-6e1f7b2c9a5d",
        short_name: "TVM",
        name: "TV Moemlingen",
        logo_url: "https://placehold.co/120x120?text=TVM"
      },
      {
        uuid: "9a6b2c1f-7d4e-4b2c-8f1a-2d6c7b1e5f9a",
        short_name: "SSV",
        name: "SSV Marktoberdorf",
        logo_url: "https://placehold.co/120x120?text=SSV"
      },
      {
        uuid: "2f9a6c1b-4d7e-4b2f-8a5c-1e6d2b7c9f3a",
        short_name: "VCL",
        name: "VC Mauerstetten",
        logo_url: "https://placehold.co/120x120?text=VCL"
      }
    ]
  },
  "/api/plan": {
    stages: [
      {
        id: 1,
        name: "Gruppenphase",
        groups: [
          {
            id: "b1b6f2d7-6cc7-4c8c-9c1a-2b3f5e7a8d90",
            name: "A",
            teams: [
              {
                uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
                played: 3,
                wins: 3,
                lost: 0,
                sets_won: 9,
                sets_lost: 2,
                ball_points_won: 225,
                ball_points_lost: 182,
                points: 9
              },
              {
                uuid: "0e1a9b36-71d0-4b6d-9a44-2b6b5af5b0c2",
                played: 3,
                wins: 2,
                lost: 1,
                sets_won: 7,
                sets_lost: 5,
                ball_points_won: 211,
                ball_points_lost: 205,
                points: 6
              },
              {
                uuid: "3d9b1f2c-9c2a-4f02-8dd5-5c8f0f2bcb3f",
                played: 3,
                wins: 1,
                lost: 2,
                sets_won: 4,
                sets_lost: 7,
                ball_points_won: 190,
                ball_points_lost: 214,
                points: 3
              },
              {
                uuid: "b8b2f14d-6d32-4f8a-8c87-9d8b2a5a9c11",
                played: 3,
                wins: 0,
                lost: 3,
                sets_won: 2,
                sets_lost: 9,
                ball_points_won: 176,
                ball_points_lost: 216,
                points: 0
              }
            ]
          },
          {
            id: "c2a7d1e4-0b83-4b7f-9a6c-1f2d3e4b5c6d",
            name: "B",
            teams: [
              {
                uuid: "9e3f2d61-8f85-4c34-9b7d-0f6f3c62d1a9",
                played: 3,
                wins: 3,
                lost: 0,
                sets_won: 9,
                sets_lost: 1,
                ball_points_won: 228,
                ball_points_lost: 170,
                points: 9
              },
              {
                uuid: "6c6b3d25-0f9a-4c62-9f4e-7a1f6f2e3b9a",
                played: 3,
                wins: 2,
                lost: 1,
                sets_won: 6,
                sets_lost: 4,
                ball_points_won: 205,
                ball_points_lost: 197,
                points: 6
              },
              {
                uuid: "2f7a9c1d-6e54-4c1b-8b9a-3f2d6b1c7e5a",
                played: 3,
                wins: 1,
                lost: 2,
                sets_won: 4,
                sets_lost: 6,
                ball_points_won: 192,
                ball_points_lost: 203,
                points: 3
              },
              {
                uuid: "4b1c7e2a-9d5f-4b2c-8c3f-1e7a5d2b9f4c",
                played: 3,
                wins: 0,
                lost: 3,
                sets_won: 1,
                sets_lost: 9,
                ball_points_won: 168,
                ball_points_lost: 220,
                points: 0
              }
            ]
          },
          {
            id: "d3c8e2f5-1c94-4d80-8b7d-2a3b4c5d6e7f",
            name: "C",
            teams: [
              {
                uuid: "7a2b9c1e-5d6f-4c2a-8b3f-9e1a7c2d5f6b",
                played: 3,
                wins: 3,
                lost: 0,
                sets_won: 9,
                sets_lost: 2,
                ball_points_won: 221,
                ball_points_lost: 182,
                points: 9
              },
              {
                uuid: "1f6b2c9a-4d7e-4b1c-8a3f-5c2d7e1b9f6a",
                played: 3,
                wins: 2,
                lost: 1,
                sets_won: 7,
                sets_lost: 4,
                ball_points_won: 210,
                ball_points_lost: 196,
                points: 6
              },
              {
                uuid: "6a2f9c1e-4d7b-4a2c-8f3e-1b7c2d5f9a6b",
                played: 3,
                wins: 1,
                lost: 2,
                sets_won: 4,
                sets_lost: 7,
                ball_points_won: 188,
                ball_points_lost: 210,
                points: 3
              },
              {
                uuid: "3b7d2f9a-1c6e-4b2f-9a5c-7e2b1f6c9d4a",
                played: 3,
                wins: 0,
                lost: 3,
                sets_won: 2,
                sets_lost: 9,
                ball_points_won: 174,
                ball_points_lost: 218,
                points: 0
              }
            ]
          },
          {
            id: "e4d9f306-2da5-4e91-9c8e-3b4c5d6e7f80",
            name: "D",
            teams: [
              {
                uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
                played: 3,
                wins: 3,
                lost: 0,
                sets_won: 9,
                sets_lost: 1,
                ball_points_won: 230,
                ball_points_lost: 171,
                points: 9
              },
              {
                uuid: "5d1b7c2a-9f6e-4b3c-8a2d-6e1f7b2c9a5d",
                played: 3,
                wins: 2,
                lost: 1,
                sets_won: 6,
                sets_lost: 5,
                ball_points_won: 206,
                ball_points_lost: 200,
                points: 6
              },
              {
                uuid: "9a6b2c1f-7d4e-4b2c-8f1a-2d6c7b1e5f9a",
                played: 3,
                wins: 1,
                lost: 2,
                sets_won: 4,
                sets_lost: 7,
                ball_points_won: 187,
                ball_points_lost: 209,
                points: 3
              },
              {
                uuid: "2f9a6c1b-4d7e-4b2f-8a5c-1e6d2b7c9f3a",
                played: 3,
                wins: 0,
                lost: 3,
                sets_won: 2,
                sets_lost: 9,
                ball_points_won: 172,
                ball_points_lost: 221,
                points: 0
              }
            ]
          }
        ]
      },
      {
        id: 2,
        name: "Viertelfinale",
        matches: [
          {
            id: "c9b0c3c5-9b5c-4f4f-86b8-9d2d6c11a4e1",
            home_uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
            away_uuid: "4b1c7e2a-9d5f-4b2c-8c3f-1e7a5d2b9f4c",
            sets_home: 2,
            sets_away: 0,
            status: "finished"
          },
          {
            id: "a7d2f8a0-1c7e-4d83-9c7a-6e0a8a7d4c5b",
            home_uuid: "9e3f2d61-8f85-4c34-9b7d-0f6f3c62d1a9",
            away_uuid: "3d9b1f2c-9c2a-4f02-8dd5-5c8f0f2bcb3f",
            sets_home: 2,
            sets_away: 1,
            status: "finished"
          },
          {
            id: "b8c3d2e1-2f7a-4e82-8c6b-4d2c1b0a9f8e",
            home_uuid: "7a2b9c1e-5d6f-4c2a-8b3f-9e1a7c2d5f6b",
            away_uuid: "6c6b3d25-0f9a-4c62-9f4e-7a1f6f2e3b9a",
            sets_home: 2,
            sets_away: 0,
            status: "finished"
          },
          {
            id: "d4e5f6a7-3b8c-4d9e-8f0a-1b2c3d4e5f6a",
            home_uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
            away_uuid: "1f6b2c9a-4d7e-4b1c-8a3f-5c2d7e1b9f6a",
            sets_home: 2,
            sets_away: 1,
            status: "finished"
          }
        ]
      },
      {
        id: 3,
        name: "Halbfinale",
        matches: [
          {
            id: "e1f2a3b4-5c6d-4e7f-8a9b-0c1d2e3f4a5b",
            home_uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
            away_uuid: "9e3f2d61-8f85-4c34-9b7d-0f6f3c62d1a9",
            sets_home: 2,
            sets_away: 1,
            status: "finished"
          },
          {
            id: "f2a3b4c5-6d7e-4f80-9a1b-2c3d4e5f6a7b",
            home_uuid: "7a2b9c1e-5d6f-4c2a-8b3f-9e1a7c2d5f6b",
            away_uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
            sets_home: 1,
            sets_away: 2,
            status: "finished"
          }
        ]
      },
      {
        id: 4,
        name: "Finale",
        matches: [
          {
            id: "a1b2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
            home_uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
            away_uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
            sets_home: 2,
            sets_away: 0,
            status: "finished"
          }
        ]
      }
    ]
  },
  "/api/live": {
    courts: [
      {
        id: "court-1",
        name: "Court 1",
        match: {
          home_uuid: "e5b01a1b-3c7f-4f27-8d0f-4a0b4f5f2b41",
          away_uuid: "0e1a9b36-71d0-4b6d-9a44-2b6b5af5b0c2",
          sets_home: 1,
          sets_away: 0,
          points_home: 18,
          points_away: 14,
          status: "live"
        }
      },
      {
        id: "court-2",
        name: "Court 2",
        match: {
          home_uuid: "9e3f2d61-8f85-4c34-9b7d-0f6f3c62d1a9",
          away_uuid: "6c6b3d25-0f9a-4c62-9f4e-7a1f6f2e3b9a",
          sets_home: 2,
          sets_away: 1,
          points_home: 21,
          points_away: 19,
          status: "live"
        }
      },
      {
        id: "court-3",
        name: "Court 3",
        match: {
          home_uuid: "7a2b9c1e-5d6f-4c2a-8b3f-9e1a7c2d5f6b",
          away_uuid: "1f6b2c9a-4d7e-4b1c-8a3f-5c2d7e1b9f6a",
          sets_home: 0,
          sets_away: 1,
          points_home: 12,
          points_away: 18,
          status: "live"
        }
      },
      {
        id: "court-4",
        name: "Court 4",
        match: {
          home_uuid: "8c2d7f1a-5b6e-4c2a-9f1b-6d7c2a5e9b3f",
          away_uuid: "5d1b7c2a-9f6e-4b3c-8a2d-6e1f7b2c9a5d",
          sets_home: 1,
          sets_away: 1,
          points_home: 20,
          points_away: 20,
          status: "live"
        }
      }
    ],
    stats: [
      { id: 1, label: "Possession", value: "62%" },
      { id: 2, label: "Fouls", value: "7" },
      { id: 3, label: "Timeouts", value: "3" }
    ]
  }
};

export async function fetchJson(endpoint) {
  await delay(450);

  if (!(endpoint in database)) {
    throw new Error(`Unknown endpoint: ${endpoint}`);
  }

  return JSON.parse(JSON.stringify(database[endpoint]));
}
