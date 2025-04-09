import streamlit as st
import pandas as pd
import time
from datetime import datetime
import requests
import re
import os  # Add import for file path handling

# Update the GitHub path for products.csv
GITHUB_PRODUCTS_PATH = "https://github.com/wineguy-maker/lcbo/blob/e471f608a1947bfa4e49cf211f1bd884063e58ae/products.csv"
GITHUB_FAVORITES_PATH = "https://github.com/wineguy-maker/lcbo/blob/e471f608a1947bfa4e49cf211f1bd884063e58ae/favorites.csv"

# -------------------------------
# Data Handling
# -------------------------------
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    return df
    
def load_food_items():
    try:
        food_items = pd.read_csv('food_items.csv')
        return food_items
    except Exception as e:
        st.error(f"Error loading food items: {e}")
        return pd.DataFrame(columns=['Category', 'FoodItem'])
        
def sort_data(data, column):
    sorted_data = data.sort_values(by=column, ascending=False)
    return sorted_data

# -------------------------------
# Filter functions
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
    elif sort_by == 'Top Viewed - Year':
        data = data.sort_values(by='raw_view_rank_yearly', ascending=True)
    elif sort_by == 'Top Veiwed - Month':
        data = data.sort_values(by='raw_view_rank_monthly', ascending=True)
    elif sort_by == 'Top Seller - Year':
        data = data.sort_values(by='raw_sell_rank_yearly', ascending=True)
    elif sort_by == 'Top Seller - Month':
        data = data.sort_values(by='raw_sell_rank_monthly', ascending=True)
    else:
        data = data.sort_values(by='weighted_rating', ascending=False)
    return data

def filter_data(data, country='All Countries', region='All Regions', varietal='All Varietals', exclude_usa=False, in_stock=False, only_vintages=False, store='Select Store'):
    if country != 'All Countries':
        data = data[data['raw_country_of_manufacture'] == country]
    if region != 'All Regions':
        data = data[data['raw_lcbo_region_name'] == region]
    if varietal != 'All Varietals':
        data = data[data['raw_lcbo_varietal_name'] == varietal]
    if store != 'Select Store':
        data = data[data['store_name'] == store]
    if in_stock:
        data = data[data['stores_inventory'] > 0]
    if only_vintages:
        data = data[data['raw_lcbo_program'].str.contains(r"['\"]Vintages['\"]", regex=True, na=False)]
    if exclude_usa:
        data = data[data['raw_country_of_manufacture'] != 'United States']
    return data

# -------------------------------
# Helper: Transform Image URL
# -------------------------------
def transform_image_url(url, new_size):
    """
    Replace the ending pattern (e.g., '319.319.PNG') in the URL with the new size string.
    new_size should include extension, e.g., '2048.2048.png' or '1280.1280.png'.
    """
    if not isinstance(url, str):
        return url
    # This regex finds a pattern like "digits.digits.ext" at the end of the URL
    return re.sub(r"\d+\.\d+\.(png|PNG)$", new_size, url)

# -------------------------------
# Refresh function
# -------------------------------
def refresh_data(store_id=None):
    current_time = datetime.now()
    st.info("Refreshing data...")

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
        st.info(f"Total Count: {total_count}")

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
                ],
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
            time.sleep(1)  # Avoid hitting the server too frequently

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
                'raw_ec_promo_price': raw_data.get('ec_promo_price', 'N/A'),
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
                'stores_inventory': raw_data.get('stores_inventory', 0),
                'raw_online_inventory': raw_data.get('online_inventory', 0),
                'raw_avg_reviews': raw_data.get('avg_reviews', 0),
                'raw_ec_rating': raw_data.get('ec_rating', 0),
                'weighted_rating': 0.0,  # Placeholder for weighted rating
                'raw_view_rank_yearly': raw_data.get('view_rank_yearly', 'N/A'),
                'raw_view_rank_monthly': raw_data.get('view_rank_monthly', 'N/A'),
                'raw_sell_rank_yearly': raw_data.get('sell_rank_yearly', 'N/A'),
                'raw_sell_rank_monthly': raw_data.get('sell_rank_monthly', 'N/A')
            }
            products.append(product_info)

        
        df_products = pd.DataFrame(products)

        # Debug: Log the number of products retrieved
        st.write(f"Retrieved {len(df_products)} products.")

        # Calculate mean rating for products with reviews
        valid_reviews = pd.to_numeric(df_products['raw_avg_reviews'], errors='coerce')
        valid_ratings = pd.to_numeric(df_products['raw_ec_rating'], errors='coerce')
        mean_rating = valid_ratings[valid_reviews > 0].mean()
        minimum_votes = 10  # Minimum number of votes required

        def weighted_rating(R, v, m, C):
            # Calculate IMDb-style weighted rating
            return (v / (v + m)) * R + (m / (v + m)) * C

        # Compute weighted rating using numeric conversion
        df_products['weighted_rating'] = df_products.apply(
            lambda x: weighted_rating(
                float(x['raw_ec_rating']) if pd.notna(x['raw_ec_rating']) and x['raw_ec_rating'] != 'N/A' else 0,
                float(x['raw_avg_reviews']) if pd.notna(x['raw_avg_reviews']) and x['raw_avg_reviews'] != 'N/A' else 0,
                minimum_votes,
                mean_rating if not pd.isna(mean_rating) else 0
            ),
            axis=1
        )

        # Save the updated products.csv file
        products_file_path = os.path.join(os.getcwd(), 'products.csv')
        df_products.to_csv(products_file_path, index=False, encoding='utf-8-sig')ex=False, encoding='utf-8-sig')
        st.success(f"products.csv file updated successfully at {products_file_path}!")            st.success("products.csv file updated successfully!")
        st.write("File last modified time:", datetime.fromtimestamp(os.path.getmtime(products_file_path)))imestamp(os.path.getmtime('products.csv')))

        # Debug: Display the first few rows of the updated fileoducts.csv: {e}")
        st.write("Updated products.csv preview:")
        st.dataframe(df_products.head())
t.write("Updated products.csv preview:")
        return load_data('products.csv')  # Load from local file
    else:
        st.error("Failed to retrieve data from the API.")        return load_data('products.csv')  # Load from local file
        return None
("Failed to retrieve data from the API.")
# -------------------------------
# Save Favorites
# -------------------------------
def save_favorite_wine(wine):
    favorites_file = 'favorites.csv'  # Save locally
    if not os.path.exists(favorites_file):favorite_wine(wine):
        pd.DataFrame([wine]).to_csv(favorites_file, index=False, encoding='utf-8-sig')cally
    else:
        favorites = pd.read_csv(favorites_file)
        if not favorites['title'].str.contains(wine['title']).any():
            favorites = pd.concat([favorites, pd.DataFrame([wine])], ignore_index=True)ites = pd.read_csv(favorites_file)
            favorites.to_csv(favorites_file, index=False, encoding='utf-8-sig')():
        else:            favorites = pd.concat([favorites, pd.DataFrame([wine])], ignore_index=True)
            st.warning("This wine is already in your favorites!")rites_file, index=False, encoding='utf-8-sig')

# ------------------------------- is already in your favorites!")
# Upload to GitHub
# -------------------------------
def upload_to_github(file_path, repo, branch, commit_message):
    token = st.secrets["GITHUB_PAT"]  # Retrieve the token from Streamlit Secrets------------------
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"ch, commit_message):
    headers = {he token from Streamlit Secrets
        "Authorization": f"token {token}",rl = f"https://api.github.com/repos/{repo}/contents/{file_path}"
        "Accept": "application/vnd.github.v3+json"    headers = {
    }token {token}",
ub.v3+json"
    # Read the file content
    with open(file_path, "rb") as file:
        content = file.read()

    # Get the current file SHA (if it exists)
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else Nonee SHA (if it exists)
requests.get(url, headers=headers)
    # Prepare the payload") if response.status_code == 200 else None
    payload = {
        "message": commit_message,d
        "content": content.encode("base64").decode("utf-8"),ayload = {
        "branch": branchssage": commit_message,
    }ncode("base64").decode("utf-8"),
    if sha:        "branch": branch
        payload["sha"] = sha

    # Upload the file
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:oad the file
        print("File uploaded successfully!")load)
    else:    if response.status_code in [200, 201]:
        print(f"Failed to upload file: {response.json()}")essfully!")

# -------------------------------file: {response.json()}")
# Main Streamlit App
# --------------------------------
def main():
    st.title("LCBO Wine Filter")--------
    # Add this line to clear the cached data
    st.cache_data.clear()
    # Initialize session state for store and image modal trigger
    if 'selected_store' not in st.session_state:    st.cache_data.clear()
        st.session_state.selected_store = 'Select Store'sion state for store and image modal trigger

    # Store Selectorn_state.selected_store = 'Select Store'
    store_options = ['Select Store', 'Bradford', 'E. Gwillimbury', 'Upper Canada', 'Yonge & Eg', 'Dufferin & Steeles']
    store_ids = {
        "Bradford": "145",tore', 'Bradford', 'E. Gwillimbury', 'Upper Canada', 'Yonge & Eg', 'Dufferin & Steeles']
        "E. Gwillimbury": "391",
        "Upper Canada": "226",
        "Yonge & Eg": "457",   "E. Gwillimbury": "391",
        "Dufferin & Steeles": "618"
    }        "Yonge & Eg": "457",
    selected_store = st.sidebar.selectbox("Store", options=store_options)

    # Refresh data if store selection changesns=store_options)
    if selected_store != st.session_state.selected_store:
        st.session_state.selected_store = selected_store
        if selected_store != 'Select Store':_store:
            store_id = store_ids.get(selected_store)ssion_state.selected_store = selected_store
            data = refresh_data(store_id=store_id)
        else:   store_id = store_ids.get(selected_store)
            data = load_data("products.csv")=store_id)
    else:        else:
        data = load_data("products.csv")")

    # Sidebar Filters with improved header
    st.sidebar.header("Filter Options 🔍")
    search_text = st.sidebar.text_input("Search", value="")
    sort_by = st.sidebar.selectbox("Sort by",
                                   ['Sort by', '# of reviews', 'Rating', 'Top Veiwed - Year', 'Top Veiwed - Month', 'Top Seller - Year',search_text = st.sidebar.text_input("Search", value="")
                                    'Top Seller - Month'])sort_by = st.sidebar.selectbox("Sort by",
    Sort by', '# of reviews', 'Rating', 'Top Veiwed - Year', 'Top Veiwed - Month', 'Top Seller - Year',
                                    'Top Seller - Month'])
    # Create filter options from data
    
    # Load food items# Create filter options from data
    food_items = load_food_items()
    
    # Get unique categoriesfood_items = load_food_items()
    categories = food_items['Category'].unique()
    
    country_options = ['All Countries'] + sorted(data['raw_country_of_manufacture'].dropna().unique().tolist())
    region_options = ['All Regions'] + sorted(data['raw_lcbo_region_name'].dropna().unique().tolist())
    varietal_options = ['All Varietals'] + sorted(data['raw_lcbo_varietal_name'].dropna().unique().tolist())country_options = ['All Countries'] + sorted(data['raw_country_of_manufacture'].dropna().unique().tolist())
    food_options = ['All Dishes'] + sorted(categories.tolist())me'].dropna().unique().tolist())
    rietal_name'].dropna().unique().tolist())
    country = st.sidebar.selectbox("Country", options=country_options)
    region = st.sidebar.selectbox("Region", options=region_options)
    varietal = st.sidebar.selectbox("Varietal", options=varietal_options)ions)
    food_category = st.sidebar.selectbox("Food Category", options=food_options)ns)
    exclude_usa = st.sidebar.checkbox("Exclude USA", value=False)ons)
    in_stock = st.sidebar.checkbox("In Stock Only", value=False)lectbox("Food Category", options=food_options)
    only_vintages = st.sidebar.checkbox("Only Vintages", value=False)
    # Add "Only On Sale" checkbox in_stock = st.sidebar.checkbox("In Stock Only", value=False)
    only_on_sale = st.sidebar.checkbox("Only On Sale", value=False)checkbox("Only Vintages", value=False)
   ox
    # Apply Filters and Sorting
    filtered_data = data.copy()
    filtered_data = filter_data(filtered_data, country=country, region=region, varietal=varietal, exclude_usa=exclude_usa,
                                in_stock=in_stock, only_vintages=only_vintages)    filtered_data = data.copy()
    filtered_data = search_data(filtered_data, search_text)iltered_data, country=country, region=region, varietal=varietal, exclude_usa=exclude_usa,
            in_stock=in_stock, only_vintages=only_vintages)
    # Apply "Only On Sale" filter
    if only_on_sale:
        filtered_data = filtered_data[pd.notna(filtered_data['raw_ec_promo_price']) & (filtered_data['raw_ec_promo_price'] != 'N/A')]ter

     # Food Category Filteringpromo_price'] != 'N/A')]
    if food_category != 'All Dishes':
        selected_items = food_items[food_items['Category'] == food_category]['FoodItem'].str.lower().tolist()
        filtered_data = filtered_data[filtered_data['raw_sysconcepts'].fillna('').apply(d_category != 'All Dishes':
            lambda x: any(item in str(x).lower() for item in selected_items)        selected_items = food_items[food_items['Category'] == food_category]['FoodItem'].str.lower().tolist()
        )]illna('').apply(
.lower() for item in selected_items)
    sort_option = sort_by if sort_by != 'Sort by' else 'weighted_rating'
    if sort_option != 'weighted_rating':
        filtered_data = sort_data_filter(filtered_data, sort_option)ted_rating'
    else:    if sort_option != 'weighted_rating':
        filtered_data = sort_data(filtered_data, sort_option)rt_option)

    st.write(f"Showing **{len(filtered_data)}** products")_data = sort_data(filtered_data, sort_option)
             
    # Paginationdata)}** products")
    page_size = 10
    total_products = len(filtered_data)
    total_pages = (total_products // page_size) + (1 if total_products % page_size else 0)
    if total_pages > 0:_products = len(filtered_data)
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)= (total_products // page_size) + (1 if total_products % page_size else 0)
    else:
        page = 1e", min_value=1, max_value=total_pages, value=1, step=1)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size        page = 1
    page_data = filtered_data.iloc[start_idx:end_idx]- 1) * page_size

    # Display Productsdx:end_idx]
    for idx, row in page_data.iterrows():
        st.markdown(f"### {row['title']}")
        if pd.notna(row.get('raw_ec_promo_price')) and row['raw_ec_promo_price'] != 'N/A':row in page_data.iterrows():
            st.markdown(f"**Price:** ~~${row['raw_ec_price']}~~ ${row['raw_ec_promo_price']}")
        else:
            st.markdown(f"**Price:** ${row['raw_ec_price']}")            st.markdown(f"**Price:** ~~${row['raw_ec_price']}~~ ${row['raw_ec_promo_price']}")
        st.markdown(f"**Rating:** {row.get('raw_ec_rating', 'N/A')} | **Reviews:** {row.get('raw_avg_reviews', 'N/A')}")

        # Add a heart icon to favorite the wineaw_ec_rating', 'N/A')} | **Reviews:** {row.get('raw_avg_reviews', 'N/A')}")
        if st.button(f"❤️ Favorite {row['title']}", key=f"favorite_{idx}"):
            save_favorite_wine(row.to_dict())        # Add a heart icon to favorite the wine
            st.success(f"Added {row['title']} to favorites!")ow['title']}", key=f"favorite_{idx}"):

        # Display the thumbnail image
        thumbnail_url = row.get('raw_ec_thumbnails', None)
        if pd.notna(thumbnail_url) and thumbnail_url != 'N/A':
            st.image(thumbnail_url, width=150)nails', None)
            # Add an "Enlarge Image" button below the thumbnail.
            with st.popover("Enlarge Image"):
                large_image_url = transform_image_url(thumbnail_url, "2048.2048.png") Add an "Enlarge Image" button below the thumbnail.
                st.image(large_image_url, use_container_width=True)):
        else:                large_image_url = transform_image_url(thumbnail_url, "2048.2048.png")
            st.write("No image available.")

        # -- Instead of a "View Details" button, use an expander --
        with st.expander("Product Details", expanded=False):
            # Here, just inline the same content you used to show in show_detailed_product_popup()-
            st.write("### Detailed Product View")
            if pd.notna(thumbnail_url) and thumbnail_url != 'N/A':used to show in show_detailed_product_popup()
                detail_image_url = transform_image_url(thumbnail_url, "1280.1280.png")
                st.image(detail_image_url, width=300)thumbnail_url != 'N/A':
            if pd.notna(row['raw_lcbo_program']) and row['raw_lcbo_program'] != 'N/A': l(thumbnail_url, "1280.1280.png")
                st.markdown(f"**Vintage**")300)
            st.markdown(f"**Title:** {row['title']}") != 'N/A': 
            st.markdown(f"**URL:** {row['uri']}")
            st.markdown(f"**Country:** {row['raw_country_of_manufacture']}")
            st.markdown(f"**Region:** {row['raw_lcbo_region_name']}")
            st.markdown(f"**Type:** {row['raw_lcbo_varietal_name']}")e']}")
            st.markdown(f"**Size:** {row['raw_lcbo_unit_volume']}")
            st.markdown(f"**Description:** {row['raw_ec_shortdesc']}")
            if pd.notna(row.get('raw_ec_promo_price')) and row['raw_ec_promo_price'] != 'N/A':rkdown(f"**Size:** {row['raw_lcbo_unit_volume']}")
                st.markdown(f"**Price:** ~~${row['raw_ec_price']}~~ ${row['raw_ec_promo_price']}")']}")
            else:['raw_ec_promo_price'] != 'N/A':
                st.markdown(f"**Price:** ${row['raw_ec_price']}")~~ ${row['raw_ec_promo_price']}")
            st.markdown(f"**Rating:** {row['raw_ec_rating']}")
            st.markdown(f"**Reviews:** {row['raw_avg_reviews']}")
            st.markdown(f"**Store Inventory:** {row['stores_inventory']}")
            st.markdown(f"**Monthly Sold Rank:** {row['raw_sell_rank_monthly']}")
            st.markdown(f"**Monthly View Rank:** {row['raw_view_rank_monthly']}")
            st.markdown(f"**Yearly Sold Rank:** {row['raw_sell_rank_yearly']}")']}")
            st.markdown(f"**Yearly View Rank:** {row['raw_view_rank_yearly']}")
            st.markdown(f"**Alcohol %:** {row['raw_lcbo_alcohol_percent']}")        st.markdown(f"**Yearly Sold Rank:** {row['raw_sell_rank_yearly']}")
            st.markdown(f"**Sugar (p/ltr):** {row['raw_lcbo_sugar_gm_per_ltr']}")**Yearly View Rank:** {row['raw_view_rank_yearly']}")
                st.markdown(f"**Alcohol %:** {row['raw_lcbo_alcohol_percent']}")
        st.markdown("---")**Sugar (p/ltr):** {row['raw_lcbo_sugar_gm_per_ltr']}")

if __name__ == "__main__":        st.markdown("---")


    main()
if __name__ == "__main__":
    main()
``` 
