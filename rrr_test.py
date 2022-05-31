import json
from time import monotonic, sleep

import requests


HOMESERVER = "http://localhost:8080"

USER_1_TOK = "syt_dGVzdA_JUXtKQUUMnolcOezckNz_2eyt3H"
USER_1_HEADERS = {"Authorization": f"Bearer {USER_1_TOK}"}

USER_2_TOK = "syt_c2Vjb25k_ElKwbhaNqTgpfgFQcStD_2aiOcs"
USER_2_HEADERS = {"Authorization": f"Bearer {USER_2_TOK}"}


def _check_for_status(result):
    # Similar to raise_for_status, but prints the error.
    if 400 <= result.status_code:
        error_msg = result.json()
        result.raise_for_status()
        print(error_msg)
        exit(0)


def _sync_and_show(room_id):
    print("Syncing . . .")
    result = requests.get(
        f"{HOMESERVER}/_matrix/client/v3/sync",
        headers=USER_1_HEADERS,
        params={"filter": json.dumps({"room": {"timeline": {"limit": 30}}})},
    )
    _check_for_status(result)
    sync_response = result.json()

    room = sync_response["rooms"]["join"][room_id]

    # Find read receipts (this assumes non-overlapping).
    read_receipt_starts = {}  # start event -> users
    read_receipt_ends = {}  # end event -> users
    for event in room["ephemeral"]["events"]:
        if event["type"] != "m.receipt":
            continue

        for event_id, content in event["content"].items():
            for mxid, receipt in content["m.read"].items():
                # Just care about the localpart of the MXID.
                mxid = mxid.split(":", 1)[0]
                read_receipt_starts.setdefault(
                    receipt.get("start_event_id"), []
                ).append(mxid)
                read_receipt_ends.setdefault(event_id, []).append(mxid)

    print(room["unread_notifications"])

    if None in read_receipt_starts:
        user_ids = ", ".join(sorted(read_receipt_starts[None]))
        print(f"v--------- {user_ids} ---------v")

    for event in room["timeline"]["events"]:
        event_id = event["event_id"]

        if event_id in read_receipt_starts:
            user_ids = ", ".join(read_receipt_starts[event_id])
            print(f"v--------- {user_ids} ---------v")

        if event["type"] == "m.room.message":
            msg = event["content"]["body"]
            print(msg)

        if event_id in read_receipt_ends:
            user_ids = ", ".join(sorted(read_receipt_ends[event_id]))
            print(f"^--------- {user_ids} ---------^")

    print()
    print()


def main():
    # Create a new room as user 2, add a bunch of messages.
    result = requests.post(
        f"{HOMESERVER}/_matrix/client/v3/createRoom",
        json={"visibility": "public", "name": f"Road to Nowhere ({monotonic()})"},
        headers=USER_2_HEADERS,
    )
    _check_for_status(result)
    room_id = result.json()["room_id"]

    # Second user joins the room.
    result = requests.post(
        f"{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/join", headers=USER_1_HEADERS
    )
    _check_for_status(result)

    # Sync user 1.
    _sync_and_show(room_id)

    # User 2 sends some messages.
    event_ids = []
    with open("road_to_no_where.txt", "r") as f:
        count = 0
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue

            # Send a msg to the room.
            result = requests.put(
                f"{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/msg{count}",
                json={
                    "msgtype": "m.text",
                    "body": f"{count: >2}: {line}",
                },
                headers=USER_2_HEADERS,
            )
            _check_for_status(result)
            event_ids.append(result.json()["event_id"])
            sleep(1)

            count += 1

            if count == 17:  # End of second verse
                break

    # User 2 sends a read receipt.
    print("@second reads to end")
    result = requests.post(
        f"{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/receipt/m.read/{event_ids[-1]}",
        headers=USER_2_HEADERS,
        json={},
    )
    _check_for_status(result)

    _sync_and_show(room_id)

    # User 1 sends a read receipt.
    print("@test reads from 3 -> 8")
    result = requests.post(
        f"{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/receipt/m.read/{event_ids[8]}/{event_ids[3]}",
        headers=USER_1_HEADERS,
        json={},
    )
    _check_for_status(result)

    _sync_and_show(room_id)

    # User 1 sends another read receipt.
    print("@test reads from 13 -> 14")
    result = requests.post(
        f"{HOMESERVER}/_matrix/client/v3/rooms/{room_id}/receipt/m.read/{event_ids[14]}/{event_ids[13]}",
        headers=USER_1_HEADERS,
        json={},
    )
    _check_for_status(result)

    _sync_and_show(room_id)


if __name__ == "__main__":
    main()
