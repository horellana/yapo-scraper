import config

import os
import sys
import json

import psycopg2

import requests
import pendulum
from pypika import Table
from pypika import PostgreSQLQuery as Query
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def send_telegram_notification(new_sales):
    for items in chunks(new_sales, 5):
        url = f" https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        text = "\n".join(f"{sale['title']} {sale['price']} {sale['url']}" for sale in items)

        url_params = {
                "chat_id": config.telegram_chat_id,
                "text": text,
        }

        response = requests.post(url, url_params)

def generate_url(search_term):
    search_term = search_term.replace(" ", "+")
    return f"https://www.yapo.cl/region_metropolitana/todos_los_avisos?ca=15_s&l=0&q={search_term}&w=1&cmn="


def get_date(item):
    year = pendulum.now().year

    months_table = {
        "Ene": "01",
        "Feb": "02",
        "Mar": "03",
        "Abr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Ago": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dic": "12"
    }

    try:
        date = item.find_element_by_class_name("date").text
        hour = item.find_element_by_class_name("hour").text

        if date in ["Hoy", "Ayer"]:
            if date == "Hoy":
                date_day = pendulum.now().day
                date_month = pendulum.now().month
            else:
                date_day = pendulum.now().subtract(days=1).day
                date_month = pendulum.now().subtract(days=1).month

            if date_month < 10:
                date_month = f"0{date_month}"
        else:
            date_day, date_month = date.split(" ")
            date_month = months_table[date_month]

        if int(date_day) < 10:
            date_day = f"0{date_day}"

        return pendulum.parse(f"{year}-{date_month}-{date_day}T{hour}:00", tz="America/Santiago").isoformat()
    except Exception as e:
        print(f"ERROR: get_date(): {e}", file=sys.stderr)
        return None


def get_url(item):
    try:
        return item.find_element_by_class_name("redirect-to-url").get_attribute("href")
    except Exception as e:
        print(f"ERROR: get_url(): {e}", file=sys.stderr)
        return None


def get_title(item):
    try:
        return item.find_element_by_class_name("title").text
    except Exception as e:
        print(f"ERROR: get_title(): {e}", file=sys.stderr)
        return None


def get_price(item):
    try:
        raw_price = item.find_element_by_class_name("price").text
        return float(raw_price.replace(".", "").split(" ")[1])
    except Exception as e:
        print(f"ERROR: get_price(): {e}", file=sys.stderr)
        return None


def find_items(driver, search_term):
    search_url = generate_url(search_term)

    print(f"Search term: {search_term}")
    print(f"GET {search_url}")

    driver.get(search_url)

    items = driver.find_elements_by_class_name("ad.listing_thumbs")

    for item in items:
        title = get_title(item)
        price = get_price(item)
        url = get_url(item)
        date = get_date(item)

        item_data = {
            "title": title,
            "price": price,
            "url": url,
            "date": date
        }

        yield item_data


def insert_items(items, search_term):
    Sales = Table("sales")
    SearchTerms = Table("search_terms")
    SearchTermSales = Table("search_term_sales")

    def get_term_id(db, term):
        query = Query \
                .into(SearchTerms) \
                .columns("name") \
                .insert(term) \
                .on_conflict(SearchTerms.name) \
                .do_update(SearchTerms.name, term) \
                .returning(SearchTerms.id)

        print(str(query))
        db.execute(str(query))
        return db.fetchone()[0]

    def relate_sale_term(db, search_term_id, sale_id):
        query = Query \
                .into(SearchTermSales) \
                .columns("search_term_id", "sale_id") \
                .insert(search_term_id, sale_id) \
                .on_conflict("search_term_id", "sale_id") \
                .do_nothing()

        print(str(query))
        db.execute(str(query))

    def get_known_sales(db):
        query = Query \
                .from_(Sales) \
                .select(Sales.id)
        query = str(query)
        print(query)

        db.execute(query)
        return [row[0] for row in db.fetchall()]

    db_name = config.db_name
    db_user = config.db_user
    db_password = config.db_password

    db_connection = psycopg2.connect(f"dbname={db_name} user={db_user} password={db_password}")
    db_cursor = db_connection.cursor()

    term_id = get_term_id(db_cursor, search_term)
    known_sales = get_known_sales(db_cursor) 

    print(known_sales)
    
    known_sales = get_known_sales(db_cursor)

    print(known_sales)
    new_sales = []

    for item in items:
        query = Query \
            .into(Sales) \
            .columns("title", "price", "url", "date") \
            .insert(item["title"],
                    item["price"],
                    item["url"],
                    item["date"]) \
            .on_conflict(Sales.url) \
            .do_update(Sales.title, item["title"]) \
            .do_update(Sales.price, item["price"]) \
            .returning(Sales.id)

        db_cursor.execute(str(query))
        sale_id = db_cursor.fetchone()[0]
        relate_sale_term(db_cursor, term_id, sale_id)

        if sale_id not in known_sales:
            new_sales.append(item)

    if len(new_sales) > 0:
        print(f"Found {len(new_sales)} new sales") 
        send_telegram_notification(new_sales)

    db_connection.commit()


def main():
    driver = None

    try:
        chromedriver_path = config.chromedriver_path

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(chromedriver_path, options=chrome_options)

        for search_term in config.terms:
            print(search_term)
            items = list(find_items(driver, search_term["title"]))
            print(json.dumps(items, indent=1))
            insert_items(items, search_term["title"])


        print(json.dumps(result, indent=1))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    finally:
        if driver is not None:
            driver.quit()


if __name__ == '__main__':
    main()
