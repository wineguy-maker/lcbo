import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import requests

# -------------------------------
# Data Handling (data_handler.py)
# -------------------------------
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    return df

def sort_data(data, column):
    sorted_data = data.sort_values(by=column, ascending=False)
    return sorted_data

# -------------------------------
# Filter functions (filter.py)
# -------------------------------
def search_data(data, search_text):
    if search_text:
        data = data[data['title'].str.contains(search_text, case=False, na=False)]
    return data

def sort_data_filter(data, sort_by):
    if sort_by == '# of reviews':
        data = data.sort_values(by='raw_avg_reviews', ascending=False)
    elif sort_by == 'Rating':
        data = data.sort_values(by='raw_ec_rating', ascending=False)
    elif sort_by == 'Yearly Views':
        data = data.sort_values(by='raw_yearly_views', ascending=False)
    elif sort_by == 'Monthly Views':
        data = data.sort_values(by='raw_monthly_views', ascending=False)
    elif sort_by == 'Yearly Sold':
        data = data.sort_values(by='raw_yearly_sold', ascending=False)
    elif sort_by == 'Monthly Sold':
        data = data.sort_values(by='raw_monthly_sold', ascending=False)
    else:
        data = data.sort_values(by='weighted_rating', ascending=False)
    return data

def filter_data(data, country='Select Country', region='Select Region', varietal='Select Varietal', in_stock=False, only_vintages=False, store='Select Store'):
    if country != 'Select Country':
        data = data[data['raw_country_of_manufacture'] == country]
    if region != 'Select Region':
        data = data[data['raw_lcbo_region_name'] == region]
    if varietal != 'Select Varietal':
        data = data[data['raw_lcbo_varietal_name'] == varietal]
    if store != 'Select Store':
        data = data[data['store_name'] == store]
    if in_stock:
        data = data[data['stores_inventory'] > 0]
    if only_vintages:
        data = data[data['raw_lcbo_program'].str.contains(r"['\"]Vintages['\"]", regex=True, na=False)]
    return data

# -------------------------------
# Refresh function (refresh_data.py)
# -------------------------------
def refresh_data(store_id=None):
    current_time = datetime.now()
    st.info("Refreshing data from API...")

    url = "https://platform.cloud.coveo.com/rest/search/v2?organizationId=lcboproduction2kwygmc"
    headers = {
        "User-Agent": "your_user_agent",
        "Accept": "application/json",
        "Authorization": "Bearer xx883b5583-07fb-416b-874b-77cce565d927",
        "Content-Type": "application/json",
        "Referer": "https://www.lcbo.com/"
    }
    
    initial_payload = {
        "q": "",
        "tab": "clp-products-wine-red_wine",
        "sort": "ec_rating descending",
        "facets": [
            {
                "field": "ec_rating",
                "currentValues": [
                    {
                        "value": "4..5inc",
                        "state": "selected"
                    }
                ]
            }
        ],
        "numberOfResults": 500,
        "firstResult": 0,
        "aq": "@ec_visibility==(2,4) @cp_browsing_category_deny<>0 @ec_category==\"Products|Wine|Red Wine\" (@ec_rating==5..5 OR @ec_rating==4..4.9)"
    }
    
    if store_id:
        dictionaryFieldContext = {
            "stores_stock": "",
            "stores_inventory": store_id,
            "stores_stock_combined": store_id,
            "stores_low_stock_combined": store_id
        }
        initial_payload.update(dictionaryFieldContext)

    def get_items(payload):
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    data = get_items(initial_payload)
    if 'results' in data:
        all_items = data['results']
        total_count = data['totalCount']
        st.write(f"Total Count: {total_count}")

        num_requests = (total_count // 500) + (1 if total_count % 500 != 0 else 0)

        for i in range(1, num_requests):
            payload = {
                "q": "",
                "tab": "clp-products-wine-red_wine",
                "sort": "ec_rating descending",
                "facets": [
                    {
                        "field": "ec_rating",
                        "currentValues": [
                            {
                                "value": "4..5inc",
                                "state": "selected"
                            }
                        ]
                    }
                ]
            },
                "numberOfResults": 500,
                "firstResult": i * 500,
                "aq": "@ec_visibility==(2,4) @cp_browsing_category_deny<>0 @ec_category==\"Products|Wine|Red Wine\" (@ec_rating==5..5 OR @ec_rating==4..4.9)"
            }
            if store_id:
                payload.update(dictionaryFieldContext)
            data = get_items(payload)
            if 'results' in data:
                all_items.extend(data['results'])
            else:
                st.error(f"Key 'results' not found in the response during pagination. Response: {data}")
            time.sleep(1)  # Add a delay to avoid hitting the server too frequently

        products = []
        for product in all_items:
            raw_data = product['raw']
            product_info = {
                'title': product.get('title', 'N/A'),
                'uri': product.get('uri', 'N/A'),
                'raw_ec_thumbnails': raw_data.get('ec_thumbnails', 'N/A'),
                'raw_ec_shortdesc': raw_data.get('ec_shortdesc', 'N/A'),
                'raw_lcbo_tastingnotes': raw_data.get('lcbo_tastingnotes', 'N/A'),
                'raw_lcbo_region_name': raw_data.get('lcbo_region_name', 'N/A'),
                'raw_country_of_manufacture': raw_data.get('country_of_manufacture', 'N/A'),
                'raw_lcbo_program': raw_data.get('lcbo_program', 'N/A'),
                'raw_created_at': raw_data.get('created_at', 'N/A'),
                'raw_is_buyable': raw_data.get('is_buyable', 'N/A'),
                'raw_ec_price': raw_data.get('ec_price', 'N/A'),
                'raw_ec_final_price': raw_data.get('ec_final_price', 'N/A'),
                'raw_lcbo_unit_volume': raw_data.get('lcbo_unit_volume', 'N/A'),
                'raw_lcbo_alcohol_percent': raw_data.get('lcbo_alcohol_percent', 'N/A'),
                'raw_lcbo_sugar_gm_per_ltr': raw_data.get('lcbo_sugar_gm_per_ltr', 'N/A'),
                'raw_lcbo_bottles_per_pack': raw_data.get('lcbo_bottles_per_pack', 'N/A'),
                'raw_sysconcepts': raw_data.get('sysconcepts', 'N/A'),
                'raw_ec_category': raw_data.get('ec_category', 'N/A'),
                'raw_ec_category_filter': raw_data.get('ec_category_filter', 'N/A'),
                'raw_lcbo_varietal_name': raw_data.get('lcbo_varietal_name', 'N/A'),
                'raw_stores_stock': raw_data.get('stores_stock', 'N/A'),
                'raw_stores_stock_combined': raw_data.get('stores_stock_combined', 'N/A'),
                'raw_stores_low_stock_combined': raw_data.get('stores_low_stock_combined', 'N/A'),
                'raw_stores_low_stock': raw_data.get('stores_low_stock', 'N/A'),
                'raw_out_of_stock': raw_data.get('out_of_stock', 'N/A'),
                'stores_inventory' : raw_data.get('stores_inventory', 'N/A'),
                'raw_online_inventory': raw_data.get('online_inventory', 'N/A'),
                'raw_avg_reviews': raw_data.get('avg_reviews', 'N/A'),
                'raw_ec_rating': raw_data.get('ec_rating', 'N/A'),
                'weighted_rating': 0.0,  # Placeholder for weighted rating
                'raw_view_rank_yearly': raw_data.get('view_rank_yearly', 'N/A'),
                'raw_view_rank_monthly': raw_data.get('view_rank_monthly', 'N/A'),
                'raw_sell_rank_yearly': raw_data.get('sell_rank_yearly', 'N/A'),
                'raw_sell_rank_monthly': raw_data.get('sell_rank_monthly', 'N/A')
            }
            products.append(product_info)  # Append each product_info dictionary to the products list

        st.write(f"Total number of products scraped: {len(products)}")

        df_products = pd.DataFrame(products)
        
        # Calculate mean rating C
        mean_rating = df_products[df_products['raw_avg_reviews'] > 0]['raw_ec_rating'].mean()
        minimum_votes = 7

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
import requests

# -------------------------------
# Data Handling (data_handler.py)
# -------------------------------
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    return df

def sort_data(data, column):
    sorted_data = data.sort_values(by=column, ascending=False)
    return sorted_data

# -------------------------------
# Filter functions (filter.py)
# -------------------------------
def search_data(data, search_text):
    if search_text:
        data = data[data['title'].str.contains(search_text, case=False, na=False)]
    return data

def sort_data_filter(data, sort_by):
    if sort_by == '# of reviews':
        data = data.sort_values(by='raw_avg_reviews', ascending=False)
    elif sort_by == 'Rating':
        data = data.sort_values(by='raw_ec_rating', ascending=False)
    elif sort_by == 'Yearly Views':
        data = data.sort_values(by='raw_yearly_views', ascending=False)
    elif sort_by == 'Monthly Views':
        data = data.sort_values(by='raw_monthly_views', ascending=False)
    elif sort_by == 'Yearly Sold':
        data = data.sort_values(by='raw_yearly_sold', ascending=False)
    elif sort_by == 'Monthly Sold':
        data = data.sort_values(by='raw_monthly_sold', ascending=False)
    else:
        data = data.sort_values(by='weighted_rating', ascending=False)
    return data

def filter_data(data, country='Select Country', region='Select Region', varietal='Select Varietal', in_stock=False, only_vintages=False, store='Select Store'):
    if country != 'Select Country':
        data = data[data['raw_country_of_manufacture'] == country]
    if region != 'Select Region':
        data = data[data['raw_lcbo_region_name'] == region]
    if varietal != 'Select Varietal':
        data = data[data['raw_lcbo_varietal_name'] == varietal]
    if store != 'Select Store':
        data = data[data['store_name'] == store]
    if in_stock:
        data = data[data['stores_inventory'] > 0]
    if only_vintages:
        data = data[data['raw_lcbo_program'].str.contains(r"['\"]Vintages['\"]", regex=True, na=False)]
    return data

# -------------------------------
# Refresh function (refresh_data.py)
# -------------------------------
def refresh_data(store_id=None):
    current_time = datetime.now()
    st.info("Refreshing data from API...")

    url = "https://platform.cloud.coveo.com/rest/search/v2?organizationId=lcboproduction2kwygmc"
    headers = {
        "User-Agent": "your_user_agent",
        "Accept": "application/json",
        "Authorization": "Bearer xx883b5583-07fb-416b-874b-77cce565d927",
        "Content-Type": "application/json",
        "Referer": "https://www.lcbo.com/"
    }
    
    initial_payload = {
        "q": "",
        "tab": "clp-products-wine-red_wine",
        "sort": "ec_rating descending",
        "facets": [
            {
                "field": "ec_rating",
                "currentValues": [
                    {
                        "value": "4..5inc",
                        "state": "selected"
                    }
                ]
            }
        ],
        "numberOfResults": 500,
        "firstResult": 0,
        "aq": "@ec_visibility==(2,4) @cp_browsing_category_deny<>0 @ec_category==\"Products|Wine|Red Wine\" (@ec_rating==5..5 OR @ec_rating==4..4.9)"
    }
    
    if store_id:
        dictionaryFieldContext = {
            "stores_stock": "",
            "stores_inventory": store_id,
            "stores_stock_combined": store_id,
            "stores_low_stock_combined": store_id
        }
        initial_payload.update(dictionaryFieldContext)

    def get_items(payload):
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    data = get_items(initial_payload)
    if 'results' in data:
        all_items = data['results']
        total_count = data['totalCount']
        st.write(f"Total Count: {total_count}")

        num_requests = (total_count // 500) + (1 if total_count % 500 != 0 else 0)

        for i in range(1, num_requests):
            payload = {
                "q": "",
                "tab": "clp-products-wine-red_wine",
                "sort": "ec_rating descending",
                "facets": [
                    {
                        "field": "ec_rating",
                        "currentValues": [
                            {
                                "value": "4..5inc",
                                "state": "selected"
                            }
                        ]
                    }
                ]
            },
                "numberOfResults": 500,
                "firstResult": i * 500,
                "aq": "@ec_visibility==(2,4) @cp_browsing_category_deny<>0 @ec_category==\"Products|Wine|Red Wine\" (@ec_rating==5..5 OR @ec_rating==4..4.9)"
            }
            if store_id:
                payload.update(dictionaryFieldContext)
            data = get_items(payload)
            if 'results' in data:
                all_items.extend(data['results'])
            else:
                st.error(f"Key 'results' not found in the response during pagination. Response: {data}")
            time.sleep(1)  # Add a delay to avoid hitting the server too frequently

        products = []
        for product in all_items:
            raw_data = product['raw']
            product_info = {
                'title': product.get('title', 'N/A'),
                'uri': product.get('uri', 'N/A'),
                'raw_ec_thumbnails': raw_data.get('ec_thumbnails', 'N/A'),
                'raw_ec_shortdesc': raw_data.get('ec_shortdesc', 'N/A'),
                'raw_lcbo_tastingnotes': raw_data.get('lcbo_tastingnotes', 'N/A'),
                'raw_lcbo_region_name': raw_data.get('lcbo_region_name', 'N/A'),
                'raw_country_of_manufacture': raw_data.get('country_of_manufacture', 'N/A'),
                'raw_lcbo_program': raw_data.get('lcbo_program', 'N/A'),
                'raw_created_at': raw_data.get('created_at', 'N/A'),
                'raw_is_buyable': raw_data.get('is_buyable', 'N/A'),
                'raw_ec_price': raw_data.get('ec_price', 'N/A'),
                'raw_ec_final_price': raw_data.get('ec_final_price', 'N/A'),
                'raw_lcbo_unit_volume': raw_data.get('lcbo_unit_volume', 'N/A'),
                'raw_lcbo_alcohol_percent': raw_data.get('lcbo_alcohol_percent', 'N/A'),
                'raw_lcbo_sugar_gm_per_ltr': raw_data.get('lcbo_sugar_gm_per_ltr', 'N/A'),
                'raw_lcbo_bottles_per_pack': raw_data.get('lcbo_bottles_per_pack', 'N/A'),
                'raw_sysconcepts': raw_data.get('sysconcepts', 'N/A'),
                'raw_ec_category': raw_data.get('ec_category', 'N/A'),
                'raw_ec_category_filter': raw_data.get('ec_category_filter', 'N/A'),
                'raw_lcbo_varietal_name': raw_data.get('lcbo_varietal_name', 'N/A'),
                'raw_stores_stock': raw_data.get('stores_stock', 'N/A'),
                'raw_stores_stock_combined': raw_data.get('stores_stock_combined', 'N/A'),
                'raw_stores_low_stock_combined': raw_data.get('stores_low_stock_combined', 'N/A'),
                'raw_stores_low_stock': raw_data.get('stores_low_stock', 'N/A'),
                'raw_out_of_stock': raw_data.get('out_of_stock', 'N/A'),
                'stores_inventory' : raw_data.get('stores_inventory', 'N/A'),
                'raw_online_inventory': raw_data.get('online_inventory', 'N/A'),
                'raw_avg_reviews': raw_data.get('avg_reviews', 'N/A'),
                'raw_ec_rating': raw_data.get('ec_rating', 'N/A'),
                'weighted_rating': 0.0,  # Placeholder for weighted rating
                'raw_view_rank_yearly': raw_data.get('view_rank_yearly', 'N/A'),
                'raw_view_rank_monthly': raw_data.get('view_rank_monthly', 'N/A'),
                'raw_sell_rank_yearly': raw_data.get('sell_rank_yearly', 'N/A'),
                'raw_sell_rank_monthly': raw_data.get('sell_rank_monthly', 'N/A')
            }
            products.append(product_info)  # Append each product_info dictionary to the products list

        st.write(f"Total number of products scraped: {len(products)}")

        df_products = pd.DataFrame(products)
        
        # Calculate mean rating C
        mean_rating = df_products[df_products['raw_avg_reviews'] > 0]['raw_ec_rating'].mean()
        minimum_votes = 50

