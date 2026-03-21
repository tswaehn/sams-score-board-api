import json
from pathlib import Path

from fetch_competition import get_competition
from fetch_competition_list import get_competition_list


def build_output_path(endpoint: str) -> Path:
    filename = endpoint.strip("/").replace("/", "_")
    return Path(__file__).with_name(f"{filename}.json")


def store_competition_list() -> None:
    competition_list = get_competition_list()
    output_path = build_output_path("competition-list")
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(competition_list, output_file, indent=2)
    print(json.dumps(competition_list, indent=2))


def test_competition():
    competition_id = "71556c84-7e05-4516-88f7-4bf890f9873a"
    competition_id = "dfcdd4c1-6d94-42ce-9028-9bba43d36d56"
    competition_id = "d2f619a3-7fea-4b1e-9d86-a300e335e2ec"
    competition_id = "d2818335-7d46-4053-bdad-9a57a98d2c05"

    payload = get_competition(competition_id)

    output_path = build_output_path("competition")
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
    print(json.dumps(payload, indent=2))



if __name__ == "__main__":
    store_competition_list()
    test_competition()
