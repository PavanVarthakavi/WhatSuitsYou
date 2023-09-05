# Importing the required libraries
import re  # Regular Expression Library for text manipulation
import time  # Time Library for delays
import openai  # OpenAI Library for API interactions
import os  # OS Library for system-level functions
import json  # JSON Library for JSON manipulation
import requests  # Library for HTTP requests
from flask import Flask, request, render_template  # Flask libraries for web application
from selenium.webdriver import Chrome  # Web scraping using Selenium
from selenium.common.exceptions import InvalidArgumentException  # Exception handling in Selenium
from dotenv import load_dotenv  # For environment variables
from bs4 import BeautifulSoup  # For HTML parsing

# Load environment variables from a .env file
load_dotenv()

# Fetch and set OpenAI API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OpenAI API Key")
openai.api_key = api_key

# Function to get store URLs based on store names
def get_site_urls_from_store_names(store_names):
    if not store_names:  
        return []
    # Using GPT-4 to fetch the URLs
    store_to_url_prompt = f"Could you provide the URLs for the following fashion stores: {', '.join(store_names)}?"
    store_urls_str = call_chat_gpt(store_to_url_prompt)
    # Extracting URLs using Regular Expression
    store_urls = list(set(re.findall(r'https?://[^\s\]\[)]+', store_urls_str)))
    return store_urls

# Function to get recommended sites based on style and price range
def get_recommended_sites_from_chat_gpt(recommended_style, price_range):
    site_prompt = f"Which online stores would you recommend for someone interested in {recommended_style} fashion within a {price_range} price range?"
    recommended_sites_str = call_chat_gpt(site_prompt)
    recommended_sites = [site.strip() for site in recommended_sites_str.split(',') if site.strip()]
    return recommended_sites

# Function to manage API calls to OpenAI's GPT-4 model
def call_chat_gpt(prompt):
    model_engine = "gpt-4"  # Specifying model engine
    retries = 3  # Number of retries
    delay = 10  # Delay time in seconds
    
    # Exception handling and API call logic
    for i in range(retries):
        try:
            # API call
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=[{"role": "system", "content": "You are a helpful assistant."},
                          {"role": "user", "content": prompt}]
            )
            suggestion = response['choices'][0]['message']['content'].strip()
            return suggestion
        except openai.error.RateLimitError:  # Handling rate limit exceeded errors
            if i < retries - 1:
                print(f"Rate limit exceeded. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Rate limit exceeded. Exiting.")
                return "Rate limit exceeded"

# Function to perform Google Custom Search for images
def search_google_images(api_key, cse_id, query, age, gender, num_results=10):
    modified_query = f"{query} for {age} year old {gender} site: https://unsplash.com/s/photos/fashion/"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cse_id, 'q': modified_query, 'searchType': 'image', 'num': num_results}
    
    try:
        # API call to Google Custom Search
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()
        
        # Extracting image links from the API response
        if 'items' in results and isinstance(results['items'], list):
            image_links = [item['link'] for item in results['items'][6: -2]]
        else:
            image_links = []
    except requests.RequestException as e:  # Handling request errors
        print(f"An error occurred: {e}")
        image_links = []
        
    return image_links

# Flask Web Application
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Fetch form data
        height = request.form['height']
        age = request.form['age']
        gender = request.form['gender']
        weight = request.form['weight']
        preferred_style = request.form['preferred_style']
        price_range = request.form['price_range']
        
        # Generate prompt for GPT-4
        style_prompt = f"Given the user's profile: {age} years old, {gender}, {height} tall, {weight} in weight, preferring {preferred_style} within a {price_range} price range, what style would you recommend?"
        recommended_styles_str = call_chat_gpt(style_prompt)
        recommended_styles = [style.strip() for style in recommended_styles_str.split(',') if style.strip()]
        
        # Fetch recommended sites
        recommended_stores = get_recommended_sites_from_chat_gpt(recommended_styles_str, price_range)
        recommended_sites = get_site_urls_from_store_names(recommended_stores)
        
        # Limit to top 6 recommended sites
        if recommended_sites:
            recommended_sites = recommended_sites[:6]
        
        # Fetching Google API credentials
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")

        # Image fetching
        images_for_styles = {}
        for style in recommended_styles:
            images = search_google_images(google_api_key, cse_id, style, age, gender)
            images_for_styles[style] = images

        # Rendering HTML template
        return render_template('results.html', recommended_styles=recommended_styles, recommended_sites=recommended_sites, images_for_styles=images_for_styles)
        
    return render_template('index.html')

# Running the Flask app
if __name__ == '__main__':
    app.run(debug=True)
