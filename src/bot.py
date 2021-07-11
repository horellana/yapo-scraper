import config

import json

import pendulum
import requests
import psycopg2
from pypika import Table
from pypika import PostgreSQLQuery as Query, Order


Chats = Table("telegram_chats")
Messages = Table("telegram_commands")
SearchTerms = Table("search_terms")
ChatSearchTerms = Table("telegram_chat_search_terms")

URL = f"https://api.telegram.org/bot{config.telegram_bot_token}/getUpdates"


def send_telegram_notification(msg):
    url = f" https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    url_params = {
            "chat_id": config.telegram_chat_id,
            "text": msg,
    }

    return requests.post(url, url_params)


def connect_to_db():
    db_name = config.db_name
    db_user = config.db_user
    db_password = config.db_password

    db_connection = psycopg2.connect(f"dbname={db_name} user={db_user} password={db_password}")

    return db_connection


def get_last_processed_message(db):
    query = Query.from_(Messages).select(Messages.date).orderby(Messages.date, order=Order.desc).limit(1)
    query = str(query)
    print(query)
    
    db.execute(query)
    return db.fetchone()[0]


def get_commands():
    print(f"GET {URL}")
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
        "id": command["message"]["message_id"],
        "date": pendulum.from_timestamp(command["message"]["date"]).isoformat(),
        "chat_id": command["message"]["chat"]["id"],
        "command_action": command_name,
        "command_arg": " ".join(command_arg)
    }

    return result


def insert_telegram_chat(db, chat_id):
    query = Query.into(Chats).columns("id").insert(chat_id).on_conflict("id").do_nothing()
    query = str(query)

    print(query)
    db.execute(query)


def insert_telegram_action(db, action_id, chat_id, action_name, action_args):
    query = Query \
            .into(Commands) \
            .columns("id", "telegram_chat_id", "command", "parameters") \
            .insert(action_id, chat_id, action_name, action_args) \
            .on_conflict("id") \
            .do_nothing()

    query = str(query)
    print(query)
    db.execute(query)


def create_search_term(db, chat_id, search_term_name):
    query = Query \
                .into(SearchTerms) \
                .columns("name") \
                .insert(search_term_name) \
                .on_conflict(SearchTerms.name) \
                .do_update(SearchTerms.name, search_term_name) \
                .returning(SearchTerms.id)

    query = str(query)
    print(query)

    db.execute(query)
    search_term_id = db.fetchone()[0]

    query = Query.into(ChatSearchTerms) \
            .columns("telegram_chat_id", "search_term_id") \
            .insert(chat_id, search_term_id) \
            .on_conflict("telegram_chat_id", "search_term_id") \
            .do_nothing()

    query = str(query)
    print(query)

    db.execute(query)


def insert_command(db, command):
    action = command["command_action"]
    args = command["command_arg"]

    query = Query \
            .into("telegram_commands") \
            .columns("id", "telegram_chat_id", "date", "command", "args") \
            .insert(command["id"], command["chat_id"], command["date"], action, args) \
            .on_conflict("date").do_nothing()

    query = str(query)
    print(query)
    db.execute(query)


def handle_command(db, command):
    action = command["command_action"]
    args = command["command_arg"]

    print(f"action: {action}")
    print(f"args: {args}")

    if action == "/add_search":
        create_search_term(db, command["chat_id"], args)
        insert_command(db, command)
        send_telegram_notification(f"Search '{args}' added")

    elif action == "/list_searchs":
        query = Query \
                .from_(SearchTerms) \
                .left_join(ChatSearchTerms) \
                .on(ChatSearchTerms.search_term_id == SearchTerms.id) \
                .select(SearchTerms.name) \
                .where(ChatSearchTerms.telegram_chat_id == command["chat_id"])

        query = str(query)
        print(query)

        db.execute(query)
        searchs = db.fetchall()
        
        insert_command(db, command)
        send_telegram_notification("\n".join(str(s[0]) for s in searchs))

    elif action == "/delete_search":
        query = Query \
                .from_(ChatSearchTerms) \
                .left_join(SearchTerms) \
                .on(ChatSearchTerms.search_term_id == SearchTerms.id) \
                .where(SearchTerms.name == args) \
                .where(ChatSearchTerms.telegram_chat_id == command["chat_id"]) \
                .delete()

        query = str(query)
        print(query)

        db.execute(query)

        send_telegram_notificatin(f"Search {args} deleted")


def main():
    try:
        db = connect_to_db()
        

        newest_command_date = pendulum.parse(get_last_processed_message(db.cursor()).isoformat()).int_timestamp

        print(newest_command_date)

        for command in get_commands():
            db_cursor = db.cursor()
            parsed = parse_command(command)
            
            print(parsed)
            
            print(newest_command_date)
            print(pendulum.parse(parsed["date"]).int_timestamp)

            if newest_command_date is not None:
                if pendulum.parse(parsed["date"]).int_timestamp <= newest_command_date:
                    print("Ignoring old command")
                    continue

            insert_telegram_chat(db_cursor, parsed["chat_id"])

            try:
                handle_command(db_cursor, parsed)
                db.commit()
            except Exception as e:
                print(f"Error when handling command: {parsed}: {e}")
                db.rollback()
                continue

    finally:
        if db is not None:
            db.commit()
            db.close()
         

if __name__ == "__main__":
    main()
