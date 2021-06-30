import config

import json

import pendulum
import requests
import psycopg2
from pypika import Table
from pypika import PostgreSQLQuery as Query, Order


Messages = Table("telegram_messages")

URL = f"https://api.telegram.org/bot{config.telegram_bot_token}/getUpdates"


def get_last_processed_message(db):
    query = Query.from_(Messages).select(Messages.date).orderby(Messages.date, order=Order.desc).limit(1)
    query = str(query)
    print(query)


def get_commands():
    response = requests.get(URL)
    response_json = response.json()

    for message in response.json()["result"]:
        if "entities" not in message["message"]:
            continue

        yield message

    return response.json()["result"]


def parse_command(command):
    command_text = command["message"]["text"]
    (command_name, *command_arg) = command_text.split(" ")

    result = {
        "date": pendulum.from_timestamp(command["message"]["date"]).isoformat(),
        "chat_id": command["message"]["chat"]["id"],
        "command_action": command_name,
        "command_arg": " ".join(command_arg)
    }

    return result


def main():
    for command in get_commands():
        print(json.dumps(command, indent=1))
        parsed = parse_command(command)
        print(parsed)

    # print(json.dumps(list(get_commands()), indent=1))
    # print("main()")
    # db_connection = None

    # try:
    #     connection_string = f"dbname={config.db_name} host={config.db_host} userw={config.db_user} password={config.db_password}"

    #     if hasattr(config, "db_port"):
    #         connection_string = f"{connection_string} port={config.db_port}"

    #     print(f"Db connection string: {connection_string}")

    #     db_connection = psycopg2.connect(connection_string)
    #     latest_message = get_last_processed_message(db_connection.cursor())
    # finally:
    #     if db_connection is not None:
    #         db_connection.commit()
    #         db_connection.close()

if __name__ == "__main__":
    main()
