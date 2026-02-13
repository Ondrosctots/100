import streamlit as st
import requests
import re
import time

# --- API Helper Class ---
class ReverbManager:
    def __init__(self, token):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/hal+json",
            "Accept": "application/hal+json",
            "Accept-Version": "3.0"
        }
        self.base_url = "https://api.reverb.com/api"

    def get_listing_id(self, url):
        match = re.search(r'item/(\d+)', url)
        return match.group(1) if match else None

    def fetch_source(self, listing_id):
        res = requests.get(f"{self.base_url}/listings/{listing_id}", headers=self.headers)
        return res.json() if res.status_code == 200 else None

    def create_draft(self, src, ship_id):
        # 50% Price Calculation
        try:
            amount = float(src.get("price", {}).get("amount", "0").replace(",", ""))
            new_price = f"{(amount * 0.5):.2f}"
        except: new_price = "0.00"

        payload = {
            "make": src.get("make"),
            "model": src.get("model"),
            "title": src.get("title"),
            "description": src.get("description"),
            "offers_enabled": False,
            "shipping_profile_id": int(ship_id),
            "price": {"amount": new_price, "currency": src.get("price", {}).get("currency", "USD")}
        }
        
        # Category & Condition mapping
        if src.get("categories"): payload["categories"] = [{"uuid": src["categories"][0].get("uuid")}]
        if src.get("condition"): payload["condition"] = {"uuid": src["condition"].get("uuid")}
        
        # Photos
        photo_urls = []
        for p in src.get("photos", []):
            url = p.get("_links", {}).get("large_crop", {}).get("href") or p.get("_links", {}).get("full", {}).get("href")
            if url: photo_urls.append(url)
        payload["photos"] = photo_urls

        return requests.post(f"{self.base_url}/listings", headers=self.headers, json=payload)

    def get_drafts(self):
        res = requests.get(f"{self.base_url}/my/listings?state=draft", headers=self.headers)
        return res.json().get("listings", []) if res.status_code == 200 else []

    def publish(self, listing_id):
        res = requests.put(f"{self.base_url}/listings/{listing_id}", headers=self.headers, json={"publish": True})
        return res.status_code in [200, 201, 204]

# --- Streamlit UI ---
st.set_page_config(page_title="Reverb Manager", layout="wide")

if "token" not in st.session_state:
    st.title("🔑")
    token_input = st.text_input("Enter 🔑:", type="password")
    if st.button("Connect"):
        if token_input:
            st.session_state.token = token_input
            st.rerun()
    st.stop()

api = ReverbManager(st.session_state.token)
tab1, tab2, tab3 = st.tabs(["🆕 Create Drafts", "📋 Manage Drafts", "✅ Live History"])

# --- TAB 1: CLONING ---
with tab1:
    st.header("Bulk Clone at 50% Off")
    urls_input = st.text_area("Paste URLs (one per line or comma-separated)")
    ship_id = st.text_input("Shipping Profile ID")
    
    if st.button("Generate Drafts"):
        urls = [u.strip() for u in urls_input.replace("\n", ",").split(",") if u.strip()]
        progress = st.progress(0)
        for i, url in enumerate(urls):
            l_id = api.get_listing_id(url)
            src = api.fetch_source(l_id)
            if src:
                res = api.create_draft(src, ship_id)
                if res.status_code in [201, 202]:
                    st.toast(f"Created: {src['title']}")
                else:
                    st.error(f"Failed {url}: {res.status_code}")
            time.sleep(2) # Safety delay
            progress.progress((i + 1) / len(urls))
        st.success("Batch Complete!")

# --- TAB 2: MANAGEMENT ---
with tab2:
    st.header("Drafts Ready to Publish")
    drafts = api.get_drafts()
    for d in drafts:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{d['title']}**")
            c1.write(f"Price: {d['price']['amount']} | ID: {d['id']}")
            if c2.button("🚀 Publish", key=f"p_{d['id']}"):
                if api.publish(d['id']):
                    st.success(f"Published {d['id']}!")
                    time.sleep(1)
                    st.rerun()

# --- TAB 3: HISTORY ---
with tab3:
    st.header("Recently Live")
    st.info("Check your Reverb dashboard to see all live listings.")
