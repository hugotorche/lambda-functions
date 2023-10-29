import os
import json
import requests
import pandas as pd
from time import sleep
import psycopg2

def lambda_handler(event, context):

    # Set DB connection
    db_connection = {
        'user': 'hugotorche',
        'password': os.environ.get['AWS_RDS_PASSWORD'],
        'host': os.environ.get['AWS_RDS_HOST'],
        'port': '5432',
        'database': 'huto'
    }

    conn = psycopg2.connect(
        dbname=db_connection['database'],
        user=db_connection['user'],
        password=db_connection['password'],
        host=db_connection['host'],
        port=db_connection['port']
    )

    cur = conn.cursor()

    # Init variables
    counter = 0
    brand = 'loccitane'
    pages = 2

    # First call for total view
    url = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601'
    payload = {'applicationId': os.environ.get['RAKUTEN_APP_ID'],
            'hits': 30,
            'keyword': brand, # Brands can be lowercase english or japanese
            'page': 1,
            'postageFlag': 1
            }
    r = requests.get(url, params=payload)
    resp = r.json()
    df_rows = []

    # Loop through the pages 
    for i in range(1, pages):
        url = 'https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601'
        payload = {'applicationId': os.environ.get['RAKUTEN_APP_ID'],
            'hits': 30,
            'keyword': brand,
            'page': 1,
            'postageFlag': 1
            }
        r = requests.get(url, params=payload)
        resp = r.json()

        for i in resp['Items']:
            counter = counter + 1
            item = i['Item']

            # Get genres from csv loading 
            df_genres = pd.read_csv('genres_map.csv')
            df_genres['GENRE_ID'] = df_genres['GENRE_ID'].astype(int)
            print('【Genre Id】', item['genreId'])
            print('【Genre Name】', str(df_genres.loc[df_genres['GENRE_ID'] == int(item['genreId']),'GENRE_NAME'].values[0]))
            
            # Append row data to df 
            d = {
                'SOURCE': 'RAKUTEN ICHIBA',
                'BRAND': str(brand).upper(),
                'ITEM_CODE': str(item['itemCode']),
                'ITEM_NAME': str(item['itemName']),
                'PRICE': int(item['itemPrice']),
                'ITEM_URL': str(item['itemUrl']),
                'SHOP_NAME': str(item['shopName']),
                'SHOP_URL': str(item['shopUrl']),
                'GENRE_ID': str(item['genreId']),
                'GENRE_NAME': str(df_genres.loc[df_genres['GENRE_ID'] == int(item['genreId']),'GENRE_NAME'].values[0]),
                'GIFT_FLAG': str(item['giftFlag']),
                'REVIEW_AVERAGE': float(item['reviewAverage']),
                'REVIEW_COUNT': int(item['reviewCount'])
            }
            df_rows.append(d)
            sleep(0.1)

    # Define the SQL query with placeholders
    query = """
    INSERT INTO public.f_rakuten ("SOURCE", "BRAND", "ITEM_CODE", "ITEM_NAME", "PRICE", "ITEM_URL", "SHOP_NAME", "SHOP_URL", "GENRE_ID", "GENRE_NAME", "GIFT_FLAG", "REVIEW_AVERAGE", "REVIEW_COUNT")
    VALUES (%(SOURCE)s, %(BRAND)s, %(ITEM_CODE)s, %(ITEM_NAME)s, %(PRICE)s, %(ITEM_URL)s, %(SHOP_NAME)s, %(SHOP_URL)s, %(GENRE_ID)s, %(GENRE_NAME)s, %(GIFT_FLAG)s, %(REVIEW_AVERAGE)s, %(REVIEW_COUNT)s)
    ON CONFLICT ("ITEM_CODE")
    DO UPDATE SET
        "SOURCE" = EXCLUDED."SOURCE",
        "BRAND" = EXCLUDED."BRAND",
        "ITEM_NAME" = EXCLUDED."ITEM_NAME",
        "PRICE" = EXCLUDED."PRICE",
        "ITEM_URL" = EXCLUDED."ITEM_URL",
        "SHOP_NAME" = EXCLUDED."SHOP_NAME",
        "SHOP_URL" = EXCLUDED."SHOP_URL",
        "GENRE_ID" = EXCLUDED."GENRE_ID",
        "GENRE_NAME" = EXCLUDED."GENRE_NAME",
        "GIFT_FLAG" = EXCLUDED."GIFT_FLAG",
        "REVIEW_AVERAGE" = EXCLUDED."REVIEW_AVERAGE",
        "REVIEW_COUNT" = EXCLUDED."REVIEW_COUNT";
    """

    # Iterate through the data and execute the query for each item
    for item in df_rows:
        cur.execute(query, item)

    # Commit the changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Data has been sent to the PostgreSQL table!')
    }
