import os
import json
import requests
import hashlib
import hmac
import datetime
from urllib.parse import quote

# Amazon PA-API 5.0 Credentials
# Amazon PA-API 5.0 Credentials (Set these in GitHub Secrets)
ACCESS_KEY = os.environ.get("AMAZON_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("AMAZON_SECRET_KEY", "")
PARTNER_TAG = os.environ.get("AMAZON_PARTNER_TAG", "")
REGION = "us-east-1"
HOST = "webservices.amazon.com"
ENDPOINT = "https://webservices.amazon.com/paapi5/searchitems"

# Path helpers
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_FILE = os.path.join(ROOT_DIR, "data", "HiddenOffersDaily", "products.json")

def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

def get_signature_key(key, date_stamp, region_name, service_name):
    k_date = sign(("AWS4" + key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region_name)
    k_service = sign(k_region, service_name)
    k_signing = sign(k_service, "aws4_request")
    return k_signing

def fetch_deals():
    """
    Fetches print book deals from Amazon PA-API.
    Note: This is a simplified PA-API 5.0 SearchItems implementation.
    """
    print("Fetching Amazon deals...")
    
    if SECRET_KEY == "YOUR_SECRET_KEY":
        print("Warning: SECRET_KEY not set. Using sample data for layout testing.")
        return get_sample_data()

    # PA-API 5.0 SearchItems Request Body
    payload = {
        "Keywords": "Today's featured deals",
        "SearchIndex": "All",
        "ItemCount": 10,
        "Resources": [
            "Images.Primary.Large",
            "ItemInfo.Title",
            "ItemInfo.Features",
            "ItemInfo.ByLineInfo",
            "ItemInfo.Classifications",
            "Offers.Listings.Price",
            "Offers.Listings.DeliveryInfo.IsPrimeEligible",
            "Offers.Listings.SavingBasis"
        ],
        "PartnerTag": PARTNER_TAG,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.com"
    }
    
    body = json.dumps(payload)
    
    # AWS Signature V4 Auth (Simplified conceptual version)
    # In a real scenario, use python-amazon-paapi or a robust signer
    t = datetime.datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')
    
    canonical_uri = '/paapi5/searchitems'
    canonical_querystring = ''
    canonical_headers = f'content-encoding:amz-1.0\nhost:{HOST}\nx-amz-date:{amz_date}\nx-amz-target:com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems\n'
    signed_headers = 'content-encoding;host;x-amz-date;x-amz-target'
    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    canonical_request = f'POST\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
    
    algorithm = 'AWS4-HMAC-SHA256'
    credential_scope = f'{date_stamp}/{REGION}/ProductAdvertisingAPI/aws4_request'
    string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
    
    signing_key = get_signature_key(SECRET_KEY, date_stamp, REGION, 'ProductAdvertisingAPI')
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    authorization_header = f'{algorithm} Credential={ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
    
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'X-Amz-Date': amz_date,
        'X-Amz-Target': 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems',
        'Content-Encoding': 'amz-1.0',
        'Authorization': authorization_header
    }
    
    try:
        response = requests.post(ENDPOINT, headers=headers, data=body)
        response.raise_for_status()
        data = response.json()
        
        products = []
        for item in data.get('SearchResult', {}).get('Items', []):
            item_info = item.get('ItemInfo', {})
            offers = item.get('Offers', {}).get('Listings', [{}])[0]
            
            # Extract features (bullet points)
            features = item_info.get('Features', {}).get('DisplayValues', [])
            
            products.append({
                "title": item_info.get('Title', {}).get('DisplayValue', 'N/A'),
                "author": item_info.get('ByLineInfo', {}).get('Contributors', [{}])[0].get('Name', 'N/A'),
                "category": item_info.get('Classifications', {}).get('ProductGroup', {}).get('DisplayValue', 'N/A'),
                "image_url": item.get('Images', {}).get('Primary', {}).get('Large', {}).get('URL', ''),
                "price": offers.get('Price', {}).get('DisplayAmount', 'N/A'),
                "savings": offers.get('Price', {}).get('Savings', {}).get('DisplayAmount', '0'),
                "savings_percentage": offers.get('Price', {}).get('Savings', {}).get('Percentage', 0),
                "is_prime": offers.get('DeliveryInfo', {}).get('IsPrimeEligible', False),
                "description": "\n".join(features),
                "url": item.get('DetailPageURL', '')
            })
        
        return products
        
    except Exception as e:
        print(f"Error fetching deals: {e}")
        return get_sample_data()

def get_sample_data():
    """Returns sample data for demonstration/testing."""
    return [
        {
            "title": "Atomic Habits: An Easy & Proven Way to Build Good Habits & Break Bad Ones",
            "author": "James Clear",
            "category": "Book",
            "image_url": "https://m.media-amazon.com/images/I/513Y5o-DYtL.jpg",
            "price": "$12.99",
            "savings": "$14.01",
            "savings_percentage": 52,
            "is_prime": True,
            "description": "An Easy & Proven Way to Build Good Habits & Break Bad Ones.\nOver 10 million copies sold.\nTiny Changes, Remarkable Results.",
            "url": "https://www.amazon.com/dp/0735211299"
        },
        {
            "title": "The Psychology of Money: Timeless lessons on wealth, greed, and happiness",
            "author": "Morgan Housel",
            "category": "Book",
            "image_url": "https://m.media-amazon.com/images/I/41r6F2LRf8L.jpg",
            "price": "$11.49",
            "savings": "$7.51",
            "savings_percentage": 40,
            "is_prime": True,
            "description": "Timeless lessons on wealth, greed, and happiness.\nDoing well with money isn’t necessarily about what you know.",
            "url": "https://www.amazon.com/dp/0857197681"
        }
    ]

def save_products(new_products):
    existing_products = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
        except Exception:
            existing_products = []
            
    # Use URL as a unique identifier to avoid duplicates
    existing_urls = {p['url'] for p in existing_products}
    
    unique_new_products = [p for p in new_products if p['url'] not in existing_urls]
    
    combined_products = existing_products + unique_new_products
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(combined_products, f, indent=4)
    print(f"Added {len(unique_new_products)} new products. Total: {len(combined_products)}")

def main():
    products = fetch_deals()
    if products:
        save_products(products)

if __name__ == "__main__":
    main()
