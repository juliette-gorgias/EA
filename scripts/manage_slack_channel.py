#!/usr/bin/env python3
"""
Slack channel management utility.

Requires env vars:
  SLACK_USER_TOKEN   - xoxp-... user token with scopes: channels:read, channels:write,
                       groups:read, groups:write (for private channels)
  SLACK_BOT_TOKEN    - xoxb-... bot token with scope: channels:manage (optional,
                       needed to invite the bot before renaming private channels)

Usage:
  python3 scripts/manage_slack_channel.py --channel cx-leadership --action deprecate-and-recreate
"""

import argparse
import os
import sys
import requests


SLACK_API = "https://slack.com/api"


def api(method: str, token: str, **kwargs) -> dict:
    resp = requests.post(
        f"{SLACK_API}/{method}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=kwargs,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data.get('error')}")
    return data


def find_channel(token: str, name: str) -> dict:
    """Return channel dict for the given name (searches public + private)."""
    for channel_type in ("public_channel,private_channel",):
        cursor = ""
        while True:
            params = {"types": channel_type, "limit": 200, "exclude_archived": True}
            if cursor:
                params["cursor"] = cursor
            resp = requests.get(
                f"{SLACK_API}/conversations.list",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            ).json()
            if not resp.get("ok"):
                raise RuntimeError(f"conversations.list failed: {resp.get('error')}")
            for ch in resp.get("channels", []):
                if ch["name"] == name:
                    return ch
            cursor = resp.get("response_metadata", {}).get("next_cursor", "")
            if not cursor:
                break
    raise RuntimeError(f"Channel #{name} not found")


def get_members(token: str, channel_id: str) -> list[str]:
    resp = requests.get(
        f"{SLACK_API}/conversations.members",
        headers={"Authorization": f"Bearer {token}"},
        params={"channel": channel_id, "limit": 200},
    ).json()
    if not resp.get("ok"):
        raise RuntimeError(f"conversations.members failed: {resp.get('error')}")
    return resp.get("members", [])


def deprecate_and_recreate(user_token: str, channel_name: str, bot_token: str | None = None):
    print(f"Looking up #{channel_name}...")
    ch = find_channel(user_token, channel_name)
    channel_id = ch["id"]
    is_private = ch.get("is_private", False)
    print(f"  Found: {channel_id} ({'private' if is_private else 'public'})")

    # Get members before archiving
    members = get_members(user_token, channel_id)
    print(f"  Members: {len(members)}")

    # If private and bot token provided, invite bot so it can participate
    if is_private and bot_token:
        bot_info = requests.get(
            f"{SLACK_API}/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"},
        ).json()
        bot_user_id = bot_info.get("user_id")
        if bot_user_id and bot_user_id not in members:
            print(f"  Inviting bot ({bot_user_id}) to channel...")
            try:
                api("conversations.invite", user_token, channel=channel_id, users=bot_user_id)
            except RuntimeError as e:
                print(f"  Warning: {e}")

    # Rename
    deprecated_name = f"{channel_name}-deprecated"
    print(f"  Renaming to #{deprecated_name}...")
    api("conversations.rename", user_token, channel=channel_id, name=deprecated_name)

    # Archive
    print(f"  Archiving #{deprecated_name}...")
    api("conversations.archive", user_token, channel=channel_id)

    # Create new public channel
    print(f"  Creating new public #{channel_name}...")
    new_ch = api("conversations.create", user_token, name=channel_name, is_private=False)
    new_id = new_ch["channel"]["id"]
    print(f"  New channel id: {new_id}")

    # Invite original members (creator is auto-added)
    me = requests.get(
        f"{SLACK_API}/auth.test",
        headers={"Authorization": f"Bearer {user_token}"},
    ).json().get("user_id")
    to_invite = [m for m in members if m != me]
    if bot_token:
        bot_user_id = requests.get(
            f"{SLACK_API}/auth.test",
            headers={"Authorization": f"Bearer {bot_token}"},
        ).json().get("user_id")
        to_invite = [m for m in to_invite if m != bot_user_id]

    if to_invite:
        print(f"  Inviting {len(to_invite)} members...")
        api("conversations.invite", user_token, channel=new_id, users=",".join(to_invite))

    print(f"\nDone! #{channel_name} is now public ({new_id}). Old channel archived as #{deprecated_name}.")


def main():
    parser = argparse.ArgumentParser(description="Slack channel management utility")
    parser.add_argument("--channel", required=True, help="Channel name (without #)")
    parser.add_argument(
        "--action",
        required=True,
        choices=["deprecate-and-recreate"],
        help="Action to perform",
    )
    args = parser.parse_args()

    user_token = os.environ.get("SLACK_USER_TOKEN")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not user_token:
        print("Error: SLACK_USER_TOKEN env var required", file=sys.stderr)
        sys.exit(1)

    if args.action == "deprecate-and-recreate":
        deprecate_and_recreate(user_token, args.channel, bot_token)


if __name__ == "__main__":
    main()
