import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import io
from PIL import Image
import numpy as np
import json
from collections import defaultdict
import math

# 🖥️ Page Configuration
st.set_page_config(page_title="Amazon Advertising Dashboard", layout="wide")

# --- Inicjalizacja stanu sesji ---
if 'rules' not in st.session_state:
    try:
        with open("rules.json", 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
            # Konwersja starych reguł do nowego formatu (jeśli jest to potrzebne)
            for rule in rules_data:
                if 'type' not in rule:
                    rule['type'] = 'Bid'
                if 'value_type' not in rule:
                    rule['value_type'] = 'Wpisz wartość'
                if 'color' not in rule:
                    rule['color'] = 'Czerwony'
                if 'highlight_column' not in rule: # Dodaj nową kolumnę, jeśli nie istnieje
                    rule['highlight_column'] = rule.get('metric', 'ACOS')
            st.session_state.rules = rules_data
    except (FileNotFoundError, json.JSONDecodeError):
        # Inicjalizacja z kilkoma pustymi regułami, jeśli plik nie istnieje lub jest pusty
        st.session_state.rules = [{"type": "Bid", "name": "", "metric": "ACOS", "condition": "Większe niż", "value": 0.0, "change": 0.0, "value_type": "Wpisz wartość", "color": "Czerwony", "highlight_column": "ACOS"} for _ in range(5)]


if 'manual_bid_updates' not in st.session_state:
    st.session_state.manual_bid_updates = None
if 'new_bid_data' not in st.session_state:
    st.session_state.new_bid_data = {}
if 'bulk_bid_change' not in st.session_state:
    st.session_state.bulk_bid_change = {} # Słownik do przechowywania zmian % per widok
# --- KONIEC ---


# --- START CSS SECTION ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Poppins', sans-serif; }
.stApp { background-color: #F7F5EF !important; }
h1, h3 { color: #333; }
[data-testid="stTabs"] { margin-top: 1rem !important; } /* Adjusted margin for global selector */
.main .block-container { padding-top: 2rem; }
[data-testid="stVerticalBlock"]:has(> [data-testid="stAgGrid"]), [data-testid="stVerticalBlock"]:has(> [data-testid="stDataFrame"]) {
    background-color: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.05);
}
.main-filter-container [data-testid="stSelectbox"] > div > div {
    background-color: #F45D48 !important; border-radius: 10px !important; border: none !important; color: white !important;
}
.main-filter-container [data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #F45D48 !important; border-radius: 10px !important;
}
.main-filter-container [data-testid="stSelectbox"] div, .main-filter-container [data-testid="stSelectbox"] input { color: white !important; }
.main-filter-container [data-testid="stSelectbox"] svg { fill: white !important; }
div[data-baseweb="popover"] li { background-color: #F45D48 !important; color: white !important; }
div[data-baseweb="popover"] li:hover { background-color: #ff7b68 !important; }
.stRadio > label { font-size: 1.1rem; font-weight: 600; color: #333; padding-bottom: 10px; }
.stTextInput input { background-color: white !important; border: 1px solid #E0E0E0 !importante; border-radius: 8px; height: 42px; }
div[data-testid="stHorizontalBlock"] { align-items: center; }
p.filter-label { font-weight: 600; color: #333; margin: 0; text-align: right; padding-right: 10px; }
</style>
""", unsafe_allow_html=True)
# --- END CSS SECTION ---


# --- CONFIGURATION AND CONSTANTS ---
# Data structure for multiple accounts

# Original data for ZIPRO
KRAJE_MAPA_ZIPRO = {
    "Niemcy":    {"tab_id": "10fe_YpeNoM8LqelCf9RQ3uUnQgl6CmnCRm1y6xklBLg", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Włochy":    {"tab_id": "1F1oz4DTU0XCHy3KHWorIzkpgJKLpDtL3VFO0o4h49_U", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Francja":   {"tab_id": "1wU7xCI89Nu4sxCNtrYMo9XtVzP30Xjo1MRbQTL-GBOk", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Hiszpania": {"tab_id": "1AbKJ8fm1fg8aFu9gxATvI2xc1UQmgBd1FaNLDYQ84L8", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Holandia":  {"tab_id": "16FneIVf1KdN_QKF8LKJNcq5KC3bt8RcJwTo7q9fFR4Y", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Belgia":    {"tab_id": "1W0NmnYVfWNylNu6QGJBEjI_HADKZiqZNI0cHhVpepe4", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Polska":    {"tab_id": "15_JPk20Zu3Jk_-AaMQhmJGUTnLm0HfJGF7_Rf1aWu3Q", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"}
}

# Updated Vendor account data
KRAJE_MAPA_VENDOR = {
    "Niemcy":    {"tab_id": "1MBONeSttzovc9Qsre_G1yEdo_E6s3O6hYkVFb6GkI14", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Włochy":    {"tab_id": "1jG3wYEFzIAN4qDCxsh8L48liT5QXNyQeScWTlN-KZqw", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Francja":   {"tab_id": "1T8P8m32c887a0Ia10qrsr-TwA-ddkSZFgkl0SC6NNW0", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Hiszpania": {"tab_id": "1myCaPbiAAG-R50QnwhUubZKku1smybJRc8IkjbHpkFA", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Holandia":  {"tab_id": "", "SP_TYDZIEN": "", "SP_MIESIAC": "", "SB_TYDZIEN": "", "SB_MIESIAC": "", "SD_TYDZIEN": "", "SD_MIESIAC": "", "AK_TYDZIEN": "", "AK_MIESIAC": ""},
    "Belgia":    {"tab_id": "", "SP_TYDZIEN": "", "SP_MIESIAC": "", "SB_TYDZIEN": "", "SB_MIESIAC": "", "SD_TYDZIEN": "", "SD_MIESIAC": "", "AK_TYDZIEN": "", "AK_MIESIAC": ""},
    "Polska":    {"tab_id": "", "SP_TYDZIEN": "", "SP_MIESIAC": "", "SB_TYDZIEN": "", "SB_MIESIAC": "", "SD_TYDZIEN": "", "SD_MIESIAC": "", "AK_TYDZIEN": "", "AK_MIESIAC": ""}
}

# Data for Morele.net account
KRAJE_MAPA_MORELE = {
    "Niemcy":    {"tab_id": "1prpvbtXsf-Hx5Tm16Bt8WvR0F9ArzYOyYv3TGXH4OlY", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Włochy":    {"tab_id": "1WVw58mEujn0zRvAONi7rsIn6XOMirq7y7x66jWhglXc", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Francja":   {"tab_id": "1Qh10wof_KTeoUvQX8q0lMJuzgjxAtAQHUIgcOX4S8jE", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Hiszpania": {"tab_id": "12S_SEJIptcb1APpfODhlDGbHpE7bg-OzCCpDjSwnHkY", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Holandia":  {"tab_id": "1FhbO0YRGuwphcIV702O5orNuLgqVNUVaViPr5qvg13Y", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Belgia":    {"tab_id": "1S8P-JnQ7j-7fFe8EZsgny5DOjp5FcT93psZyqm8Mxp8", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"},
    "Polska":    {"tab_id": "1AmlWnM8iSpclQT2cu9PGx7EK0LXTCd6KxPVp3YEUTOg", "SP_TYDZIEN": "0", "SP_MIESIAC": "1199906508", "SB_TYDZIEN": "1257325307", "SB_MIESIAC": "11375362", "SD_TYDZIEN": "8043683", "SD_MIESIAC": "304910120", "AK_TYDZIEN": "797863318", "AK_MIESIAC": "2039975432"}
}

# Main dictionary to hold all account configurations
ACCOUNTS_DATA = {
    "ZIPRO": KRAJE_MAPA_ZIPRO,
    "Vendor": KRAJE_MAPA_VENDOR,
    "Morele.net": KRAJE_MAPA_MORELE
}

# --- GLOBAL ACCOUNT SELECTION INITIALIZATION ---
if 'selected_account' not in st.session_state:
    st.session_state.selected_account = list(ACCOUNTS_DATA.keys())[0]

NUMERIC_COLS = ["Spend","Sales","Orders","Daily budget","Impressions","Clicks","CTR", "CR", "Bid","Bid_new","Price","Quantity","ACOS","CPC","ROAS","Units"]


# --- MAPOWANIE KRAJÓW ---
KRAJ_CODE_MAP = {
    "Niemcy": "DE",
    "Włochy": "IT",
    "Francja": "FR",
    "Hiszpania": "ES",
    "Holandia": "NL",
    "Belgia": "BE",
    "Polska": "PL"
    # Dodaj UK jeśli jest potrzebne
    # "UK": "UK"
}


# --- HELPER FUNCTIONS ---

def get_url(tab_id, gid):
    return f"https://docs.google.com/spreadsheets/d/{tab_id}/export?format=csv&gid={gid}"

@st.cache_data
def load_price_data():
    url = "https://docs.google.com/spreadsheets/d/1Ds_SbZ3Ilg9KbipNyj-FP0V5Bb2mZFmUWoLvRhqxDCA/export?format=csv&gid=1384320249"
    try:
        df = pd.read_csv(url, header=0, dtype=str)

        # 1. Price and Name
        if df.shape[1] < 3:
            st.warning("Arkusz cen nie ma wystarczającej liczby kolumn do pobrania cen i nazw produktów.")
            price_name_map_df = pd.DataFrame(columns=['SKU', 'Price', 'Nazwa produktu'])
        else:
            price_name_map_df = df.iloc[:, [0, 1, 2]].copy()
            price_name_map_df.columns = ['SKU', 'Price', 'Nazwa produktu']
            price_name_map_df.dropna(subset=['SKU'], inplace=True)
            price_name_map_df['SKU'] = price_name_map_df['SKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # 2. Quantity
        if df.shape[1] < 29:
            qty_map_df = pd.DataFrame(columns=['SKU', 'Quantity'])
        else:
            qty_map_df = df.iloc[:, [27, 28]].copy()
            qty_map_df.columns = ['SKU', 'Quantity']
            qty_map_df.dropna(subset=['SKU'], inplace=True)
            qty_map_df['SKU'] = qty_map_df['SKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # Łączenie
        final_df = pd.merge(price_name_map_df, qty_map_df, on='SKU', how='left')

        # Konwersja
        final_df['Price'] = pd.to_numeric(final_df['Price'].astype(str).str.replace(',', '.'), errors='coerce')
        final_df['Quantity'] = pd.to_numeric(final_df['Quantity'], errors='coerce')
        final_df['Nazwa produktu'] = final_df['Nazwa produktu'].astype(str).fillna('')

        final_df = final_df.drop_duplicates(subset=['SKU'], keep='first')
        return final_df

    except Exception as e:
        st.error(f"Błąd podczas ładowania danych o cenach: {e}")
        return pd.DataFrame(columns=['SKU', 'Price', 'Quantity', 'Nazwa produktu'])


@st.cache_data
def load_product_details():
    """
    Ładuje szczegóły produktu (nazwa, marka, kategoria, ID, SKU, ASIN) z centralnego arkusza Google.
    Poprawka: Wczytuje kolumnę 'ID' z arkusza i używa jej jako 'ID' oraz 'SKU' w aplikacji, zgodnie z mapowaniem użytkownika.
    """
    url = "https://docs.google.com/spreadsheets/d/1ywoA6ZgmrPa-CUdZGbkhgp8y6ryMCCDgBgEFfvKJbPc/export?format=csv&gid=0"
    try:
        # 1. Zmienione use_cols - wczytujemy kolumny, które istnieją w arkuszu.
        # (Usunięto 'SKU', ponieważ w arkuszu nazywa się 'ID')
        use_cols = ['ID', 'ASIN', 'Nazwa', 'Marka', 'Kategoria']
        df = pd.read_csv(url, usecols=use_cols, dtype=str, header=0)

        # 2. Czyszczenie wczytanych danych
        # Kolumna 'ID' z arkusza to nasz klucz (i jednocześnie SKU)
        df['ID'] = df['ID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df['ASIN'] = df['ASIN'].astype(str).str.strip()

        # 3. Utworzenie kolumny 'SKU' na podstawie kolumny 'ID' (zgodnie z "ID (czyli sku)")
        df['SKU'] = df['ID']

        # 4. Zmieniamy nazwy kolumn na te, których oczekuje reszta aplikacji (małe litery)
        df.rename(columns={
            'Kategoria': 'kategoria',
            'Marka': 'marka',
            'Nazwa': 'nazwa'
            # ID, SKU, ASIN już mają poprawne nazwy lub zostały utworzone
        }, inplace=True)

        # 5. Wypełnianie brakujących danych pustym stringiem
        df['kategoria'] = df['kategoria'].fillna('')
        df['marka'] = df['marka'].fillna('')
        df['nazwa'] = df['nazwa'].fillna('')
        df['SKU'] = df['SKU'].fillna('')
        df['ASIN'] = df['ASIN'].fillna('')
        df['ID'] = df['ID'].fillna('')

        # 6. Usuwanie duplikatów po ID (który jest naszym kluczem głównym)
        df.drop_duplicates(subset=['ID'], keep='first', inplace=True)

        # 7. Zwracamy DataFrame z wszystkimi wymaganymi kolumnami
        # Upewnijmy się, że kolejność jest poprawna dla reszty kodu
        return df[['ID', 'SKU', 'ASIN', 'nazwa', 'marka', 'kategoria']]

    except Exception as e:
        # Zaktualizowany komunikat o błędzie
        st.error(f"Błąd podczas ładowania szczegółów produktów: {e}. Sprawdź, czy arkusz pod adresem '{url.replace('/export?format=csv&gid=0','')}' jest poprawnie udostępniony ('Każda osoba mająca link') i czy zawiera kolumny: 'ID', 'ASIN', 'Nazwa', 'Marka', 'Kategoria'.")
        # Zwracamy pusty DataFrame z oczekiwanymi (docelowymi) kolumnami w razie błędu
        return pd.DataFrame(columns=['ID', 'SKU', 'ASIN', 'nazwa', 'marka', 'kategoria'])


    except Exception as e:
        st.error(f"Błąd podczas ładowania szczegółów produktów: {e}. Sprawdź, czy arkusz pod adresem '{url.replace('/export?format=csv&gid=0','')}' jest poprawnie udostępniony ('Każda osoba mająca link') i czy zawiera kolumny 'Kategoria', 'Marka', 'Nazwa', 'ID', 'SKU', 'ASIN'.")
        # Zwracamy pusty DataFrame z oczekiwanymi (docelowymi) kolumnami w razie błędu
        return pd.DataFrame(columns=['ID', 'SKU', 'ASIN', 'nazwa', 'marka', 'kategoria'])



# <--- POCZĄTEK POPRAWIONEJ FUNKCJI ---
# PODMIEŃ CAŁĄ TĘ FUNKCJĘ W SWOIM KODZIE
@st.cache_data
def load_total_sales_and_orders(okres, country_code):
    """
    Ładuje dane o całkowitej sprzedaży i zamówieniach z oddzielnego arkusza Google.
    Używa poprawnych nazw kolumn: 'Amazon store', 'MSKU', 'Sales', 'Units sold'.
    Dodano debugowanie przed agregacją.
    """
    urls = {
        "Tydzień": "https://docs.google.com/spreadsheets/d/1ywoA6ZgmrPa-CUdZGbkhgp8y6ryMCCDgBgEFfvKJbPc/export?format=csv&gid=1591650234",
        "Miesiąc": "https://docs.google.com/spreadsheets/d/1ywoA6ZgmrPa-CUdZGbkhgp8y6ryMCCDgBgEFfvKJbPc/export?format=csv&gid=1990490485"
    }

    url = urls.get(okres)
    if not url:
        return pd.DataFrame(columns=['ID', 'Total Sales (Total)', 'Total Orders (Total)'])

    try:
        df = pd.read_csv(url, dtype=str)
        
        required_cols = ['Amazon store', 'MSKU', 'Sales', 'Units sold']
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            st.warning(f"Brak wymaganych kolumn w pliku 'Total Sales' dla okresu {okres}. Brakujące: {', '.join(missing_cols)}. Kontynuuję bez tych danych.")
            return pd.DataFrame(columns=['ID', 'Total Sales (Total)', 'Total Orders (Total)'])

        # --- Filtracja po kraju ---
        if 'Amazon store' not in df.columns:
             st.warning(f"Brak kolumny 'Amazon store' w pliku Total Sales ({okres}) do filtrowania kraju.")
             return pd.DataFrame(columns=['ID', 'Total Sales (Total)', 'Total Orders (Total)'])

        df_country = df[df['Amazon store'].str.upper() == country_code.upper()].copy()

        if df_country.empty:
            
            return pd.DataFrame(columns=['ID', 'Total Sales (Total)', 'Total Orders (Total)'])

        # --- Konwersje i czyszczenie ---
        sales_str = df_country['Sales'].astype(str)
        sales_str_cleaned = sales_str.str.replace('.', '', regex=False).str.replace(',', '.')
        df_country['Sales_numeric'] = pd.to_numeric(sales_str_cleaned, errors='coerce').fillna(0) # Nowa kolumna tymczasowa

        df_country['Units_sold_numeric'] = pd.to_numeric(df_country['Units sold'], errors='coerce').fillna(0) # Nowa kolumna tymczasowa

        df_country['MSKU_cleaned'] = df_country['MSKU'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() # Nowa kolumna tymczasowa

        
        # --- Agregacja używa nowych, numerycznych kolumn i oczyszczonego MSKU ---
        aggregated_df = df_country.groupby('MSKU_cleaned').agg(
            Total_Sales_Total=('Sales_numeric', 'sum'), # Używamy _numeric
            Total_Orders_Total=('Units_sold_numeric', 'sum') # Używamy _numeric
        ).reset_index()

        # Zmiana nazwy kolumny klucza
        aggregated_df.rename(columns={
            'MSKU_cleaned': 'ID', # Używamy _cleaned
            'Total_Sales_Total': 'Total Sales (Total)',
            'Total_Orders_Total': 'Total Orders (Total)'
        }, inplace=True)

        return aggregated_df

    except Exception as e:
        st.error(f"Krytyczny błąd podczas ładowania danych Total Sales/Orders dla {okres} ({country_code}): {e}")
        
        return pd.DataFrame(columns=['ID', 'Total Sales (Total)', 'Total Orders (Total)'])

# <--- KONIEC POPRAWIONEJ FUNKCJI ---


def save_rules_to_file(rules, filepath="rules.json"):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=4)


def clean_numeric_columns(df):
    df_clean = df.copy()
    for c in NUMERIC_COLS:
        if c == "Price (DE)" or c not in df_clean.columns:
            continue
        # Pierwsze czyszczenie - usuwanie spacji i zamiana przecinka na kropkę
        cleaned_series = df_clean[c].astype(str).str.replace(" ", "", regex=False).str.replace(",", ".", regex=False)

        # Dodatkowe czyszczenie dla kolumn procentowych - usuwanie '%'
        if any(metric in c for metric in ["ACOS", "CTR", "CR"]):
            cleaned_series = cleaned_series.str.replace("%", "", regex=False)

        # Konwersja na typ numeryczny, błędy zamieniane na NaN
        numeric_series = pd.to_numeric(cleaned_series, errors='coerce')

        # Specjalna obsługa kolumn procentowych - dzielenie przez 100, jeśli wartości są > 1
        if any(metric in c for metric in ["ACOS", "CTR", "CR"]):
            # Sprawdzenie, czy seria nie jest pusta, czy zawiera jakiekolwiek liczby i czy maksymalna wartość jest większa niż 1
            if not numeric_series.empty and pd.notna(numeric_series).any() and numeric_series.max() > 1:
                numeric_series /= 100 # Podziel przez 100

        # Przypisanie wyczyszczonej i przekonwertowanej serii z powrotem do DataFrame
        df_clean[c] = numeric_series
    return df_clean

def apply_rules_to_bids_vectorized(df, rules):
    df = df.copy()
    if "Bid" not in df.columns or not rules:
        return df, 0

    bid_loc = df.columns.get_loc("Bid")
    if "Bid_new" not in df.columns:
        df.insert(bid_loc + 1, "Bid_new", df["Bid"])
    else:
        df["Bid_new"] = df["Bid"]

    bid_rules_list = [r for r in rules if r.get('type') == 'Bid' and r.get('name')]
    if not bid_rules_list:
        return df, 0

    rules_df = pd.DataFrame(bid_rules_list)

    unique_rule_names = rules_df['name'].unique()

    bids_changed_mask = pd.Series(False, index=df.index)
    condition_map = {"Większe niż": ">", "Mniejsze niż": "<", "Równe": "="}
    metrics_as_percent = ["ACOS", "CTR", "CR"]

    for name in unique_rule_names:
        group = rules_df[rules_df['name'] == name]

        change_value = group['change'].iloc[0]
        if pd.isna(change_value):
            continue

        group_mask = pd.Series(True, index=df.index)

        for _, condition_row in group.iterrows():
            metric = condition_row.get("metric")
            condition_text = condition_row.get("condition")
            op = condition_map.get(condition_text)
            rule_value = condition_row.get("value")

            if not all([metric, op, rule_value is not None]) or metric not in df.columns:
                group_mask = pd.Series(False, index=df.index)
                break

            row_values = df[metric].fillna(0)
            try:
                rule_value_float = float(rule_value)
                rule_value_conv = rule_value_float / 100.0 if metric in metrics_as_percent else rule_value_float
            except (ValueError, TypeError):
                # Jeśli wartość nie jest liczbą, pomiń ten warunek (lub całą regułę?)
                # Na razie pomijamy warunek - załóżmy, że jest spełniony, aby nie blokować AND
                continue


            condition_mask = pd.Series(False, index=df.index)
            if op == '>': condition_mask = row_values.gt(rule_value_conv)
            elif op == '<': condition_mask = row_values.lt(rule_value_conv)
            elif op == '=': condition_mask = row_values.eq(rule_value_conv)

            group_mask &= condition_mask

        if not group_mask.any():
            continue

        mask_to_apply = group_mask & ~bids_changed_mask & df['Bid'].notna() & (df['Bid'] > 0)

        if not mask_to_apply.any():
            continue

        try:
            multiplier = 1 + (float(change_value) / 100.0)
            if multiplier < 0: multiplier = 0
            # Użyj .loc do bezpiecznego przypisania wartości
            df.loc[mask_to_apply, "Bid_new"] = df.loc[mask_to_apply, "Bid"] * multiplier
            bids_changed_mask.loc[mask_to_apply] = True
        except (ValueError, TypeError) as e:
            st.error(f"Błąd przy obliczaniu nowej stawki dla reguły '{name}': {e}")
            continue

    if "Bid_new" in df.columns:
        df['Bid_new'] = df['Bid_new'].round(2)

    num_changed = int(bids_changed_mask.sum())
    return df, num_changed

def infer_targeting_from_name(campaign_name):
    if not isinstance(campaign_name, str): return "Manual"
    return "Auto" if "AUTO" in campaign_name.upper() else "Manual"

def find_first_existing_column(df, potential_names):
    df_cols_cleaned = {col.lower().strip(): col for col in df.columns}
    for name in potential_names:
        cleaned_name = name.lower().strip()
        if cleaned_name in df_cols_cleaned:
            return df_cols_cleaned[cleaned_name]
    return None

def process_loaded_data(df_raw, typ_kampanii_arg):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()

    POTENTIAL_CAMPAIGN_COLS = ["Campaign name (Informational only)", "Campaign Name (Informational only)", "Campaign name", "Campaign Name", "Campaign"]

    sku_col_options = ["SKU", "Advertised SKU"]
    asin_col_options = ["ASIN (Informational only)", "Advertised ASIN", "ASIN"]

    found_sku_col = find_first_existing_column(df, sku_col_options)
    if found_sku_col:
        df[found_sku_col] = df[found_sku_col].fillna('').astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        if found_sku_col != 'SKU':
            df.rename(columns={found_sku_col: 'SKU'}, inplace=True)

    found_asin_col = find_first_existing_column(df, asin_col_options)
    if found_asin_col:
        df[found_asin_col] = df[found_asin_col].fillna('').astype(str).str.strip()
        if found_asin_col != 'ASIN':
            df.rename(columns={found_asin_col: 'ASIN'}, inplace=True)

    df = clean_numeric_columns(df)

    if 'Spend' in df.columns and 'Sales' in df.columns:
        # Użyj .loc, aby uniknąć SettingWithCopyWarning
        df.loc[:, 'ACOS'] = np.where(df['Sales'] > 0, df['Spend'] / df['Sales'], 0)


    STANDARDIZED_CAMPAIGN_COL = "_Campaign_Standardized"
    actual_campaign_col = find_first_existing_column(df, POTENTIAL_CAMPAIGN_COLS)
    if actual_campaign_col:
        df.rename(columns={actual_campaign_col: STANDARDIZED_CAMPAIGN_COL}, inplace=True)

    if 'Clicks' in df.columns and 'Impressions' in df.columns and 'CTR' not in df.columns:
         df.loc[:, 'CTR'] = np.where(df['Impressions'] > 0, df['Clicks'] / df['Impressions'], 0)


    if 'Clicks' in df.columns and 'Orders' in df.columns:
        # Sprawdź, czy kolumna CR już istnieje
        if 'CR' not in df.columns:
            df.loc[:, 'CR'] = np.where(df['Clicks'] > 0, df['Orders'] / df['Clicks'], 0)


    if STANDARDIZED_CAMPAIGN_COL in df.columns:
        # Użyj .loc, aby uniknąć SettingWithCopyWarning
        df.loc[:, "Targeting type"] = df[STANDARDIZED_CAMPAIGN_COL].apply(infer_targeting_from_name)


    df['Campaign Type'] = typ_kampanii_arg

    return df

# PODMIEŃ CAŁĄ TĘ FUNKCJĘ

@st.cache_data
def load_all_product_data():
    POTENTIAL_CAMPAIGN_NAMES = ["Campaign name (Informational only)", "Campaign Name (Informational only)", "Campaign name", "Campaign Name", "Campaign"]
    all_dfs, COLUMN_MAPPING, reports_to_load = [], {
        'campaign': POTENTIAL_CAMPAIGN_NAMES,
        'sku': ["SKU", "Advertised SKU"],
        'asin': ["ASIN (Informational only)", "Advertised ASIN", "ASIN"]
    }, []

    for account, kraje_mapa in ACCOUNTS_DATA.items():
        for country, settings in kraje_mapa.items():
            
            # --- POPRAWKA TUTAJ ---
            # Dodano "AK" (Auto Keyword) do mapy GIDów, które przeszukujemy
            gids_map = {
                "Sponsored Products": (settings.get("SP_TYDZIEN"), settings.get("SP_MIESIAC")),
                "Sponsored Brands": (settings.get("SB_TYDZIEN"), settings.get("SB_MIESIAC")),
                "Sponsored Display": (settings.get("SD_TYDZIEN"), settings.get("SD_MIESIAC")),
                "Auto Keyword": (settings.get("AK_TYDZIEN"), settings.get("AK_MIESIAC")) # <-- Dodana linia
            }
            # --- KONIEC POPRAWKI ---
            
            for camp_type, gids in gids_map.items():
                for gid in gids:
                    if gid and gid != 'nan' and str(gid).strip(): # Dodatkowe sprawdzenie GID
                        reports_to_load.append({
                            'account': account,
                            'country': country,
                            'gid': str(gid).strip(), # Upewnij się, że GID jest stringiem
                            'tab_id': settings["tab_id"],
                            'campaign_type': camp_type if camp_type != "Auto Keyword" else "Sponsored Products" # Raporty AK to też SP
                        })

    if not reports_to_load:
        st.warning("Nie znaleziono żadnych poprawnych GID do załadowania danych produktów.")
        return pd.DataFrame()

    failed_reports = []
    successful_loads = 0
    for report in reports_to_load:
        try:
            url = get_url(report['tab_id'], report['gid'])
            df_temp = pd.read_csv(url, low_memory=False)
            successful_loads += 1 # Zlicz udane wczytania
            found_cols = {std: find_first_existing_column(df_temp, poss) for std, poss in COLUMN_MAPPING.items()}

            # Sprawdź, czy znaleziono kolumnę kampanii ORAZ przynajmniej SKU lub ASIN
            if not found_cols.get('campaign') or not (found_cols.get('sku') or found_cols.get('asin')):
                # Można dodać ostrzeżenie, jeśli potrzebne
                # st.warning(f"Skipping report {report['gid']} for {report['country']} - no SKU/ASIN found.")
                continue

            df_small_data = {}
            # Użyj znalezionych nazw kolumn, aby pobrać dane
            for std_name, actual_name in found_cols.items():
                if actual_name: # Tylko jeśli kolumna została znaleziona
                    df_small_data[std_name.capitalize()] = df_temp[actual_name]

            # Jeśli brakuje Sku lub Asin, ale druga kolumna istnieje, dodaj pustą kolumnę
            if 'Sku' not in df_small_data and 'Asin' in df_small_data:
                 df_small_data['Sku'] = pd.Series([None] * len(df_temp))
            elif 'Asin' not in df_small_data and 'Sku' in df_small_data:
                 df_small_data['Asin'] = pd.Series([None] * len(df_temp))


            df_small = pd.DataFrame(df_small_data)
            df_small["Account"] = report['account']
            df_small["Country"] = report['country']
            df_small["Campaign Type"] = report['campaign_type']
            all_dfs.append(df_small)
        except Exception as e:
            failed_reports.append(f"Konto: {report['account']}, Kraj: {report['country']}, Arkusz: {report['tab_id']}, GID: {report['gid']} - Błąd: {e}")

    # Wyświetl podsumowanie ładowania tylko jeśli były jakieś próby
    if reports_to_load:
         st.info(f"Próbowano załadować {len(reports_to_load)} raportów produktowych. Udane: {successful_loads}. Nieudane: {len(failed_reports)}.")


    if failed_reports:
        with st.expander("⚠️ Wystąpiły problemy podczas ładowania niektórych danych produktowych (kliknij, aby rozwinąć)"):
            for failure in failed_reports:
                st.error(failure)

    if not all_dfs:
        st.error("Nie udało się załadować żadnych danych produktowych.")
        return pd.DataFrame()

    master_df = pd.concat(all_dfs, ignore_index=True)
    for col in ['Sku', 'Asin']:
        if col in master_df.columns:
            master_df[col] = master_df[col].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().fillna('') # Dodano fillna('')

    if 'Campaign' in master_df.columns:
        master_df['Targeting Type'] = master_df['Campaign'].apply(infer_targeting_from_name)

    return master_df.fillna("")



@st.cache_data
def build_dynamic_product_map():
    report_data = load_all_product_data()

    # Sprawdzenie, czy kluczowe kolumny istnieją po załadowaniu
    if report_data.empty or ('Sku' not in report_data.columns and 'Asin' not in report_data.columns):
         st.error("Nie można zbudować mapy produktów - brak danych Sku lub Asin w załadowanych raportach.")
         # Zwróć pusty DataFrame z oczekiwanymi kolumnami, aby uniknąć błędów dalej
         return pd.DataFrame(columns=['Account', 'SKU', 'ASIN', 'Campaign', 'Campaign Type', 'Targeting Type', 'Country'])


    # Stwórz kolumny Sku/Asin jeśli ich brakuje
    if 'Sku' not in report_data.columns:
        report_data['Sku'] = ''
    if 'Asin' not in report_data.columns:
        report_data['Asin'] = ''


    # Upewnij się, że wszystkie potrzebne kolumny istnieją przed ich wybraniem
    required_cols = ['Account', 'Sku', 'Asin', 'Campaign', 'Campaign Type', 'Targeting Type', 'Country']
    available_cols = [col for col in required_cols if col in report_data.columns]

    if not available_cols:
         st.error("Nie można zbudować mapy produktów - brak wymaganych kolumn w załadowanych danych.")
         return pd.DataFrame(columns=required_cols)


    product_map = report_data[available_cols].copy()
    product_map.rename(columns={'Sku': 'SKU', 'Asin': 'ASIN'}, inplace=True) # Zmień nazwę nawet jeśli nie było 'Sku'


    # Czyszczenie i usuwanie pustych wierszy
    if 'SKU' in product_map.columns:
         product_map['SKU'] = product_map['SKU'].astype(str).str.strip()
    else:
         product_map['SKU'] = '' # Upewnij się, że kolumna istnieje

    if 'ASIN' in product_map.columns:
         product_map['ASIN'] = product_map['ASIN'].astype(str).str.strip()
    else:
         product_map['ASIN'] = '' # Upewnij się, że kolumna istnieje


    # Usuń wiersze, gdzie zarówno SKU jak i ASIN są puste
    product_map.dropna(subset=['SKU', 'ASIN'], how='all', inplace=True)
    product_map = product_map[(product_map['SKU'] != '') | (product_map['ASIN'] != '')]


    # Usuwanie duplikatów
    # Sprawdź, czy kolumny istnieją przed użyciem ich w subset
    duplicate_subset = [col for col in ['Account', 'SKU', 'ASIN'] if col in product_map.columns]
    if duplicate_subset:
         product_map.drop_duplicates(subset=duplicate_subset, keep='last', inplace=True)

    # Łączenie z danymi cenowymi
    price_data = load_price_data()
    if not price_data.empty and 'SKU' in product_map.columns and 'SKU' in price_data.columns:
        product_map = pd.merge(
            product_map,
            price_data[['SKU', 'Price', 'Quantity', 'Nazwa produktu']].drop_duplicates(subset=['SKU']), # Upewnij się, że klucze są unikalne
            on='SKU',
            how='left'
        )
        # Wypełnij NaN po merge
        if 'Price' in product_map.columns: product_map['Price'] = product_map['Price'].fillna(0)
        if 'Quantity' in product_map.columns: product_map['Quantity'] = product_map['Quantity'].fillna(0)
        if 'Nazwa produktu' in product_map.columns: product_map['Nazwa produktu'] = product_map['Nazwa produktu'].fillna('')

    elif 'SKU' not in product_map.columns:
         st.warning("Nie można połączyć danych cenowych - brak kolumny SKU w mapie produktów.")


    # Upewnij się, że kolumny 'Nazwa produktu', 'Price', 'Quantity' istnieją, nawet jeśli merge się nie powiódł
    if 'Nazwa produktu' not in product_map.columns: product_map['Nazwa produktu'] = ''
    if 'Price' not in product_map.columns: product_map['Price'] = 0.0
    if 'Quantity' not in product_map.columns: product_map['Quantity'] = 0


    return product_map


@st.cache_data
def load_search_data():
    data = build_dynamic_product_map()
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, tuple) and len(data) > 0 and isinstance(data[0], pd.DataFrame):
         # Ta część wydaje się być zabezpieczeniem przed cache zwracającym krotkę
         return data[0]

    else:
        st.error("load_search_data otrzymało nieoczekiwany typ danych.")
        return pd.DataFrame() # Zwróć pusty DataFrame w razie problemu


# <--- ZAKTUALIZOWANA FUNKCJA ---
@st.cache_data
def load_and_aggregate_by_sku(account, country, okres):
    """
    Ładuje wszystkie dane (SP, SB, SD, Tydzień, Miesiąc) dla danego konta i kraju,
    agreguje Spend i Sales po SKU, a następnie dołącza szczegóły produktu ORAZ
    dane o całkowitej sprzedaży i zamówieniach.
    Filtruje dane na podstawie wybranego okresu ('Tydzień' lub 'Miesiąc').
    """
    KRAJE_MAPA = ACCOUNTS_DATA.get(account)
    if not KRAJE_MAPA:
        return pd.DataFrame()

    settings = KRAJE_MAPA.get(country)
    if not settings:
        return pd.DataFrame()

    tab_id = settings.get("tab_id")
    if not tab_id:
        return pd.DataFrame()

    if okres == "Tydzień":
        gid_keys = ["SP_TYDZIEN", "SB_TYDZIEN", "SD_TYDZIEN", "AK_TYDZIEN"]
    elif okres == "Miesiąc":
        gid_keys = ["SP_MIESIAC", "SB_MIESIAC", "SD_MIESIAC", "AK_MIESIAC"]
    else:
        gid_keys = []
    
    all_dfs = []
    
    for key in gid_keys: 
        gid = settings.get(key)
        if gid:
            try:
                df_raw = pd.read_csv(get_url(tab_id, gid), low_memory=False)
                df_processed = process_loaded_data(df_raw, "Aggregated") 
                
                if 'SKU' in df_processed.columns and 'Spend' in df_processed.columns and 'Sales' in df_processed.columns:
                    df_temp = df_processed[['SKU', 'Spend', 'Sales']].copy()
                    all_dfs.append(df_temp)
            except Exception as e:
                
                pass
    
    if not all_dfs:
        return pd.DataFrame()

    master_df = pd.concat(all_dfs, ignore_index=True)
    master_df.dropna(subset=['SKU', 'Spend', 'Sales'], inplace=True)
    master_df = master_df[master_df['SKU'].str.strip().ne('')]
    
    if master_df.empty:
        return pd.DataFrame()

    # Agregacja danych reklamowych
    aggregated_df = master_df.groupby('SKU').agg(
        Total_Spend=('Spend', 'sum'),
        Total_Sales=('Sales', 'sum')
    ).reset_index()

    # Obliczenie ACOS
    aggregated_df['ACOS'] = np.where(
        aggregated_df['Total_Sales'] > 0,
        aggregated_df['Total_Spend'] / aggregated_df['Total_Sales'],
        0
    )
    
    aggregated_df.rename(columns={'SKU': 'ID', 'Total_Spend': 'Total Spend', 'Total_Sales': 'Total Sales'}, inplace=True)
    
    # --- KROK: Łączenie ze szczegółami produktu ---
    product_details = load_product_details()
    if not product_details.empty:
        aggregated_df = pd.merge(
            aggregated_df,
            product_details,
            on='ID',
            how='left'
        )
        # Wypełnij puste komórki (tam gdzie nie znaleziono dopasowania)
        for col in ['nazwa', 'marka', 'kategoria']:
            if col in aggregated_df.columns:
                aggregated_df[col] = aggregated_df[col].fillna('')
    else:
        # Dodaj puste kolumny, jeśli ładowanie szczegółów się nie powiodło
        aggregated_df['nazwa'] = ''
        aggregated_df['marka'] = ''
        aggregated_df['kategoria'] = ''
        
    # --- NOWY KROK: Łączenie z danymi Total Sales i Total Orders ---
    country_code = KRAJ_CODE_MAP.get(country)
    if country_code:
        total_data = load_total_sales_and_orders(okres, country_code)
        if not total_data.empty:
            aggregated_df = pd.merge(
                aggregated_df,
                total_data,
                on='ID',
                how='left'
            )
            # Wypełnij puste komórki (tam gdzie nie znaleziono dopasowania)
            aggregated_df['Total Sales (Total)'] = aggregated_df['Total Sales (Total)'].fillna(0)
            aggregated_df['Total Orders (Total)'] = aggregated_df['Total Orders (Total)'].fillna(0)
        else:
            # Dodaj puste kolumny, jeśli nie ma danych
            aggregated_df['Total Sales (Total)'] = 0.0
            aggregated_df['Total Orders (Total)'] = 0
    else:
        aggregated_df['Total Sales (Total)'] = 0.0
        aggregated_df['Total Orders (Total)'] = 0
# --- KONIEC NOWEGO KROKU ---
        
    # --- NOWY KROK: Obliczenie TACOS ---
    aggregated_df['TACOS'] = np.where(
        aggregated_df['Total Sales (Total)'] > 0,
        aggregated_df['Total Spend'] / aggregated_df['Total Sales (Total)'],
        0
    )
    # --- KONIEC NOWEGO KROKU ---
        
    # Ustawienie kolejności kolumn
    final_cols = ['ID', 'nazwa', 'marka', 'kategoria', 'Total Spend', 'Total Sales', 'ACOS', 'Total Sales (Total)', 'Total Orders (Total)', 'TACOS'] # Dodano TACOS
    # Upewnij się, że wszystkie kolumny istnieją
    existing_cols = [col for col in final_cols if col in aggregated_df.columns]
    aggregated_df = aggregated_df[existing_cols]

    return aggregated_df.sort_values(by="Total Spend", ascending=False)
# <--- KONIEC ZMIAN W FUNKCJI ---


# --- HEADER ---
header_cols = st.columns([1, 5])
with header_cols[0]:
    try: st.image(Image.open("logo.png"), width=200)
    except FileNotFoundError: st.error("Nie znaleziono pliku logo.png.")
with header_cols[1]:
    st.markdown("<h1 style='margin-top: 25px; margin-left: -40px; color: #333; font-size: 48px;'>AMAZON ADVERTISING DASHBOARD</h1>", unsafe_allow_html=True)

# --- GLOBAL ACCOUNT SELECTOR ---
st.session_state.selected_account = st.selectbox(
    "**Wybierz konto do analizy:**",
    list(ACCOUNTS_DATA.keys()),
    key="global_account_selector"
)
st.markdown("---")


# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Dashboard", "📈 New Bid", "🔍 Find Product ID", "📜 Rules", "🎯 ID ACOS", "Find Product 2"])

# <--- POCZĄTEK ZAKTUALIZOWANEJ ZAKŁADKI "Dashboard" (z dwoma filtrami kampanii) ---
# PODMIEŃ CAŁY BLOK 'with tab1:' W SWOIM KODZIE
# <--- POCZĄTEK ZAKTUALIZOWANEJ ZAKŁADKI "Dashboard" (poprawiona logika % zmiany) ---
# PODMIEŃ CAŁY BLOK 'with tab1:' W SWOIM KODZIE
with tab1:
    def calculate_summary_row(df, currency_symbol):
        if df.empty:
            return None
            
        summary_data = {}
        cols_to_sum = ['Impressions', 'Clicks', 'Spend', 'Orders', 'Sales', 'Daily budget']
        existing_cols_to_sum = [col for col in cols_to_sum if col in df.columns]
        sums = df[existing_cols_to_sum].sum()

        for col in existing_cols_to_sum:
            summary_data[col] = sums.get(col, 0)

        sum_clicks, sum_impressions, sum_spend, sum_sales, sum_orders = sums.get('Clicks', 0), sums.get('Impressions', 0), sums.get('Spend', 0), sums.get('Sales', 0), sums.get('Orders', 0)
        
        summary_data['CTR'] = (sum_clicks / sum_impressions) if sum_impressions > 0 else 0
        summary_data['CPC'] = (sum_spend / sum_clicks) if sum_clicks > 0 else 0
        summary_data['ACOS'] = (sum_spend / sum_sales) if sum_sales > 0 else 0
        summary_data['ROAS'] = (sum_sales / sum_spend) if sum_spend > 0 else 0
        summary_data['CR'] = (sum_orders / sum_clicks) if sum_clicks > 0 else 0

        if 'Spend_M' in df.columns:
            cols_m_to_sum = [f"{col}_M" for col in cols_to_sum if f"{col}_M" in df.columns]
            sums_m = df[cols_m_to_sum].sum()
            for col_m in cols_m_to_sum: summary_data[col_m] = sums_m.get(col_m, 0)
            sum_clicks_m, sum_impressions_m, sum_spend_m, sum_sales_m, sum_orders_m = sums_m.get('Clicks_M', 0), sums_m.get('Impressions_M', 0), sums_m.get('Spend_M', 0), sums_m.get('Sales_M', 0), sums_m.get('Orders_M', 0)
            summary_data['CTR_M'] = (sum_clicks_m / sum_impressions_m) if sum_impressions_m > 0 else 0
            summary_data['CPC_M'] = (sum_spend_m / sum_clicks_m) if sum_clicks_m > 0 else 0
            summary_data['ACOS_M'] = (sum_spend_m / sum_sales_m) if sum_sales_m > 0 else 0
            summary_data['ROAS_M'] = (sum_sales_m / sum_spend_m) if sum_spend_m > 0 else 0
            summary_data['CR_M'] = (sum_orders_m / sum_clicks_m) if sum_clicks_m > 0 else 0

        if df.columns.any():
            first_col_name = df.columns[0]
            summary_data[first_col_name] = "SUMA"
        
        return pd.DataFrame([summary_data]).to_dict('records')

    product_map_df = build_dynamic_product_map()

    with st.spinner("Przetwarzam dane..."):
        filter_container = st.container()
        with filter_container:
            main_cols = st.columns([1.5, 2, 0.5, 3])
            with main_cols[0]:
                konto = st.session_state.selected_account
                st.write(f"#### Aktywne konto: **{konto}**")
                KRAJE_MAPA = ACCOUNTS_DATA[konto]
                okres = st.radio("Przedział czasowy:", ["Tydzień", "Miesiąc", "Porównanie"])
            with main_cols[1]:
                st.markdown('<div class="main-filter-container">', unsafe_allow_html=True)
                
                kraje_opcje = ["Wszystko"] + list(KRAJE_MAPA.keys())
                kraj = st.selectbox("Kraj", kraje_opcje)
                
                eur_pln_rate = 0.0 
                if kraj == "Wszystko":
                    eur_pln_rate = st.number_input(
                        "Podaj kurs 1 EUR w PLN (np. 4.30)", 
                        min_value=1.0, 
                        value=4.30, 
                        step=0.01, 
                        format="%.4f",
                        key="eur_pln_rate_input",
                        help="Ten kurs zostanie użyty do przeliczenia wszystkich kwot z 'Polska' (PLN) na EUR, aby ujednolicić dane."
                    )
                    if eur_pln_rate <= 0:
                        st.error("Proszę podać kurs EUR/PLN większy od 0.")

                typ_kampanii = st.selectbox("Typ kampanii", ["Sponsored Products", "Sponsored Brands", "Sponsored Display"])
                
                if typ_kampanii == "Sponsored Products":
                    widok_options = ["Campaign", "Product ad", "Product targeting", "Keyword", "Auto keyword/ASIN"]
                elif typ_kampanii == "Sponsored Brands":
                    widok_options = ["Campaign", "Keyword", "Product targeting"]
                elif typ_kampanii == "Sponsored Display":
                    widok_options = ["Campaign", "Product ad", "Product targeting", "Audience targeting", "Contextual targeting"]
                else:
                    widok_options = ["Campaign", "Product ad", "Product targeting", "Keyword", "Audience targeting", "Contextual targeting"]
                
                widok = st.selectbox("Widok", widok_options)
                st.markdown('</div>', unsafe_allow_html=True)
            with main_cols[3]:
                st.markdown("<h4 style='text-align: center; font-weight: 600; color: #333; margin-bottom: 17px;'>Filtrowanie</h4>", unsafe_allow_html=True)
                
                search_term_product_ad = "" 
                search_term_campaign_exact = "" 
                search_term_campaign_partial = "" 

                if widok == "Product ad":
                    search_term_product_ad = st.text_input(
                        "Wyszukaj (SKU, ASIN, Nazwa):", 
                        placeholder="sku1, sku2, nazwa3...",
                        key="product_ad_search",
                        help="Wpisz wiele wartości po przecinku (logika 'LUB')."
                    )
                
                target_views_for_campaign_search = ["Product targeting", "Keyword", "Auto keyword/ASIN"]
                if widok in target_views_for_campaign_search:
                    search_term_campaign_exact = st.text_input(
                        "Wyszukaj DOKŁADNĄ Nazwę Kampanii:", 
                        placeholder="dokladna nazwa1, dokladna nazwa2...",
                        key="campaign_search_exact",
                        help="Wpisz DOKŁADNE nazwy kampanii (oddzielone przecinkiem, logika 'LUB')."
                    )
                    search_term_campaign_partial = st.text_input(
                        "Wyszukaj SŁOWO w Nazwie Kampanii:", 
                        placeholder="słowo1, słowo2...",
                        key="campaign_search_partial",
                        help="Wpisz SŁOWA kluczowe (oddzielone przecinkiem, logika 'LUB')."
                    )

                def render_metric_filter(label, key):
                    cols = st.columns([1, 1.5, 1.4])
                    cols[0].markdown(f"<p class='filter-label'>{label}</p>", unsafe_allow_html=True)
                    op = cols[1].selectbox(f"{key}_op", ["Brak", ">", "<", "="], key=f"{key}_op", label_visibility="collapsed")
                    val = cols[2].text_input(f"{key}_val", key=f"{key}_value", label_visibility="collapsed")
                    return op, val
                spend_filter, spend_value = render_metric_filter("Spend", "spend")
                sales_filter, sales_value = render_metric_filter("Sales", "sales")
                orders_filter, orders_value = render_metric_filter("Orders", "orders")
                acos_filter, acos_value = render_metric_filter("ACOS", "acos")
                roas_filter, roas_value = render_metric_filter("ROAS", "roas")
                ctr_filter, ctr_value = render_metric_filter("CTR", "ctr")
                cr_filter, cr_value = render_metric_filter("CR", "cr")
                highlight_filter_placeholder = st.empty()

        st.markdown("<br>", unsafe_allow_html=True)

        all_dfs_w, all_dfs_m = [], []
        
        if kraj == "Wszystko":
            countries_to_load = list(KRAJE_MAPA.keys())
        else:
            countries_to_load = [kraj]
            
        for country_name in countries_to_load:
            ustawienia_kraju = KRAJE_MAPA.get(country_name)
            if not ustawienia_kraju:
                continue 

            tab_id = ustawienia_kraju.get("tab_id")
            gid_w, gid_m = None, None
            
            if typ_kampanii == "Sponsored Products":
                gid_w = ustawienia_kraju.get("AK_TYDZIEN") if widok == "Auto keyword/ASIN" else ustawienia_kraju.get("SP_TYDZIEN")
                gid_m = ustawienia_kraju.get("AK_MIESIAC") if widok == "Auto keyword/ASIN" else ustawienia_kraju.get("SP_MIESIAC")
            elif typ_kampanii == "Sponsored Brands":
                gid_w, gid_m = ustawienia_kraju.get("SB_TYDZIEN"), ustawienia_kraju.get("SB_MIESIAC")
            elif typ_kampanii == "Sponsored Display":
                gid_w, gid_m = ustawienia_kraju.get("SD_TYDZIEN"), ustawienia_kraju.get("SD_MIESIAC")

            df_w_raw, df_m_raw = None, None
            try:
                if okres in ["Tydzień", "Porównanie"] and gid_w and tab_id:
                    df_w_raw = pd.read_csv(get_url(tab_id, gid_w))
                if okres in ["Miesiąc", "Porównanie"] and gid_m and tab_id:
                    df_m_raw = pd.read_csv(get_url(tab_id, gid_m))
            except Exception as e:
                st.error(f"Błąd ładowania danych źródłowych dla {country_name}: {e}")

            df_w_country = process_loaded_data(df_w_raw, typ_kampanii)
            df_m_country = process_loaded_data(df_m_raw, typ_kampanii)

            if kraj == "Wszystko" and country_name == "Polska" and eur_pln_rate > 0:
                currency_cols_to_convert = ["Spend", "Sales", "Daily budget", "Bid", "Price", "CPC"]
                
                for df_to_convert in [df_w_country, df_m_country]:
                    if df_to_convert is not None and not df_to_convert.empty:
                        for col in currency_cols_to_convert:
                            if col in df_to_convert.columns:
                                df_to_convert[col] = pd.to_numeric(df_to_convert[col], errors='coerce').fillna(0) / eur_pln_rate

            if df_w_country is not None and not df_w_country.empty:
                df_w_country['Kraj'] = country_name
                all_dfs_w.append(df_w_country)
                
            if df_m_country is not None and not df_m_country.empty:
                df_m_country['Kraj'] = country_name
                all_dfs_m.append(df_m_country)

        df_w = pd.concat(all_dfs_w, ignore_index=True) if all_dfs_w else pd.DataFrame()
        df_m = pd.concat(all_dfs_m, ignore_index=True) if all_dfs_m else pd.DataFrame()
        
        if widok == "Product ad":
            account_product_map = product_map_df[product_map_df['Account'] == konto]

            def enrich_product_ad_data(report_df, product_map):
                if report_df is None or report_df.empty:
                    return report_df
                if product_map.empty:
                    return report_df
                join_key = 'SKU' if 'SKU' in report_df.columns and not report_df['SKU'].isnull().all() else 'ASIN'
                if join_key not in report_df.columns:
                    return report_df
                
                cols_to_add_from_map = ['SKU', 'ASIN', 'Nazwa produktu', 'Price', 'Quantity']
                details_to_join = product_map[list(set(cols_to_add_from_map) & set(product_map.columns))].copy()
                
                cols_in_report = report_df.columns
                cols_to_drop_from_details = [col for col in details_to_join.columns if col in cols_in_report and col != join_key]
                details_to_join = details_to_join.drop(columns=cols_to_drop_from_details, errors='ignore')

                if not details_to_join.empty and join_key in details_to_join.columns:
                    details_to_join.drop_duplicates(subset=[join_key], inplace=True)
                    enriched_df = pd.merge(report_df, details_to_join, on=join_key, how='left')
                    return enriched_df
                else:
                    return report_df

            df_w = enrich_product_ad_data(df_w, account_product_map)
            df_m = enrich_product_ad_data(df_m, account_product_map)

        if okres == "Tydzień": df = df_w
        elif okres == "Miesiąc": df = df_m
        else: df = df_w

        if df is not None and not df.empty:
            STANDARDIZED_CAMPAIGN_COL = "_Campaign_Standardized"
            
            base = {
                "Kraj": "Kraj", 
                "Campaign": STANDARDIZED_CAMPAIGN_COL, "Match type": "Match type", "Keyword text": "Keyword text", "Targeting expression": "Product targeting expression",
                "SKU": "SKU", "Customer search term": "Customer search term", "Targeting type":"Targeting type", "Product":"Product","Portfolio":"Portfolio name (Informational only)","Entity":"Entity","State":"State",
                "ASIN":"ASIN", "Nazwa produktu": "Nazwa produktu", "Price": "Price", "Quantity": "Quantity", "Daily budget":"Daily budget",
                "Campaign Type": "Campaign Type", "Impressions":"Impressions", "Clicks":"Clicks", "CTR": "CTR", "CR": "CR", "Spend":"Spend", "CPC":"CPC",
                "Orders":"Orders", "Sales":"Sales", "ACOS":"ACOS", "ROAS":"ROAS", "Bid":"Bid"
            }

            if widok == "Product ad":
                ordered = ["Kraj", "Campaign", "Targeting type", "Campaign Type", "Entity", "State", "SKU", "ASIN", "Nazwa produktu", "Price", "Quantity", "Impressions", "Clicks", "CTR", "CR", "Spend", "CPC", "Orders", "Sales", "ACOS", "ROAS", "Bid"]
            else:
                ordered = ["Kraj", "Campaign", "Match type", "Keyword text", "Targeting expression", "Customer search term", "Targeting type", "Product", "Portfolio", "Entity", "State", "Daily budget", "Impressions", "Clicks", "CTR", "CR", "Spend", "CPC", "Orders", "Sales", "ACOS", "ROAS", "Bid"]

                if widok == "Product targeting":
                    if "Match type" in ordered: ordered.remove("Match type")
                    if "Product targeting expression" in df.columns: df["Match type"] = df["Product targeting expression"].astype(str).str.split('=', n=1).str[0]
                if widok == "Auto keyword/ASIN" and 'Match type' in df.columns:
                    df = df[df['Match type'].isna()].copy()
            
            cols_map = {k: v for k in ordered for v in [base.get(k)] if v and (v in df.columns or v == k)}

            if 'ASIN' in df.columns and 'ASIN' not in cols_map:
                cols_map['ASIN'] = 'ASIN'
            
            ordered_final = [k for k in ordered if k in cols_map or (k in df.columns and k not in cols_map)]

            if 'Entity' in df.columns: df = df[df["Entity"] == widok]

            if okres == "Porównanie" and df_m is not None and not df_m.empty:
                numeric_metrics = [c for c in NUMERIC_COLS if c not in ['Bid', 'Bid_new', 'Daily budget']]
                key_display_names = [k for k in ordered_final if k not in numeric_metrics] 
                key_source_names = list(set([cols_map.get(k, k) for k in key_display_names if cols_map.get(k,k) in df.columns]))
                metric_display_names = [k for k in ordered_final if k in numeric_metrics]
                metric_source_names = list(set([cols_map.get(k, k) for k in metric_display_names if cols_map.get(k,k) in df.columns]))
                monthly_cols_to_keep = [c for c in key_source_names + metric_source_names if c in df_m.columns]
                df_m_prepared = df_m[monthly_cols_to_keep].copy()
                rename_dict = {col: f"{col}_M" for col in metric_source_names}
                df_m_prepared.rename(columns=rename_dict, inplace=True)
                if key_source_names and not df_m_prepared.empty:
                    df = pd.merge(df, df_m_prepared, on=key_source_names, how='left')
                ordered_interleaved = []
                for col_name in ordered_final:
                    ordered_interleaved.append(col_name)
                    if col_name in metric_display_names:
                        ordered_interleaved.append(f"{col_name}_M")
                ordered_final = ordered_interleaved
            
            df_display_builder = {}
            for col_display_name in ordered_final:
                if col_display_name in cols_map:
                    col_source_name = cols_map.get(col_display_name, col_display_name)
                    if col_source_name in df.columns:
                        df_display_builder[col_display_name] = df[col_source_name]
                elif col_display_name in df.columns:
                    df_display_builder[col_display_name] = df[col_display_name]
            df_display = pd.DataFrame(df_display_builder)

            # KROK 1: Zastosuj "Reguły" z zakładki 4. To jest baza.
            df_display_rules, _ = apply_rules_to_bids_vectorized(df_display, st.session_state.rules)
            
            # KROK 2: Zastosuj filtry metryk (Spend, ACOS, etc.)
            filter_map = {
                "Spend": (spend_filter, spend_value), "Sales": (sales_filter, sales_value), "Orders": (orders_filter, orders_value),
                "ACOS": (acos_filter, acos_value), "ROAS": (roas_filter, roas_value), "CTR": (ctr_filter, ctr_value), "CR": (cr_filter, cr_value)
            }
            for col, (op, val_str) in filter_map.items():
                if op != "Brak" and val_str and col in df_display_rules.columns:
                    try:
                        val = float(val_str)
                        if col in ['ACOS', 'CTR', 'CR']: val /= 100.0
                        if op == ">": df_display_rules = df_display_rules[df_display_rules[col] > val]
                        elif op == "<": df_display_rules = df_display_rules[df_display_rules[col] < val]
                        elif op == "=": df_display_rules = df_display_rules[df_display_rules[col] == val]
                    except (ValueError, TypeError, KeyError): pass
            
            # KROK 3: Zastosuj filtry wyszukiwania tekstowego (SKU, Kampanie)
            if widok == "Product ad" and search_term_product_ad:
                search_list = [term.strip().lower() for term in search_term_product_ad.split(',') if term.strip()]
                if search_list:
                    search_cols = ['SKU', 'ASIN', 'Nazwa produktu']
                    existing_search_cols = [col for col in search_cols if col in df_display_rules.columns]
                    if not existing_search_cols:
                        st.warning("Nie można wyszukać - brak kolumn SKU, ASIN lub Nazwa produktu w tabeli.", icon="⚠️")
                    else:
                        combined_mask = pd.Series([False] * len(df_display_rules), index=df_display_rules.index)
                        for term in search_list:
                            term_mask = pd.Series([False] * len(df_display_rules), index=df_display_rules.index)
                            for col in existing_search_cols:
                                term_mask = term_mask | df_display_rules[col].astype(str).str.lower().str.contains(term, na=False)
                            combined_mask = combined_mask | term_mask
                        df_display_rules = df_display_rules[combined_mask]

            target_views_for_campaign_search = ["Product targeting", "Keyword", "Auto keyword/ASIN"]
            if widok in target_views_for_campaign_search and search_term_campaign_exact:
                search_list_campaign_exact = [term.strip().lower() for term in search_term_campaign_exact.split(',') if term.strip()]
                if search_list_campaign_exact:
                    if 'Campaign' not in df_display_rules.columns:
                        st.warning("Nie można wyszukać - brak kolumny 'Campaign' w tabeli.", icon="⚠️")
                    else:
                        exact_match_mask = df_display_rules['Campaign'].astype(str).str.lower().isin(search_list_campaign_exact)
                        df_display_rules = df_display_rules[exact_match_mask]

            if widok in target_views_for_campaign_search and search_term_campaign_partial:
                search_list_campaign_partial = [term.strip().lower() for term in search_term_campaign_partial.split(',') if term.strip()]
                if search_list_campaign_partial:
                    if 'Campaign' not in df_display_rules.columns:
                        st.warning("Nie można wyszukać - brak kolumny 'Campaign' w tabeli.", icon="⚠️")
                    else:
                        combined_mask_partial = pd.Series([False] * len(df_display_rules), index=df_display_rules.index)
                        for term in search_list_campaign_partial:
                            term_mask_partial = df_display_rules['Campaign'].astype(str).str.lower().str.contains(term, na=False)
                            combined_mask_partial = combined_mask_partial | term_mask_partial
                        df_display_rules = df_display_rules[combined_mask_partial]
            
            # --- ZMIANA: NOWY BLOK LOGIKI ZMIANY % ---
            grid_key = f"{konto}_{kraj}_{typ_kampanii}_{widok}_{okres}"

            st.markdown("---")
            with st.form(key="bid_change_form"):
                st.markdown("#### Zastosuj zmianę % do stawek (dla wszystkich wierszy poniżej)")
                form_cols = st.columns([2, 1, 1])
                with form_cols[0]:
                    # Wartość domyślna formularza jest pobierana ze stanu sesji
                    bid_perc_input = st.number_input(
                        "Wprowadź zmianę % (np. -10 lub 20)", 
                        value=st.session_state.bulk_bid_change.get(grid_key), # Pobierz zapisaną wartość
                        format="%.2f",
                        placeholder="Wpisz wartość...",
                        label_visibility="collapsed"
                    )
                with form_cols[1]:
                    apply_button = st.form_submit_button("Zastosuj / Zapisz", use_container_width=True)
                with form_cols[2]:
                    clear_button = st.form_submit_button("Wyczyść zmianę", use_container_width=True)

            if apply_button:
                # Zapisz zmianę % do pamięci sesji dla tego widoku
                st.session_state.bulk_bid_change[grid_key] = bid_perc_input
                st.toast(f"Zapisano zmianę {bid_perc_input}%. Zastosowano do tabeli.")
                st.rerun() # Wymuś odświeżenie, aby zastosować zmianę

            if clear_button:
                # Wyczyść zmianę % z pamięci sesji
                st.session_state.bulk_bid_change[grid_key] = None
                st.toast("Wyczyszczono zmianę procentową.")
                st.rerun() # Wymuś odświeżenie, aby przywrócić wartości z reguł

            # KROK 4: Zastosuj zmianę procentową (jeśli jest zapisana w sesji)
            # Ta logika wykona się na każdym przebiegu, *po* regułach z KROKU 1
            current_bulk_perc = st.session_state.bulk_bid_change.get(grid_key)
            if current_bulk_perc is not None:
                if 'Bid' in df_display_rules.columns and 'Bid_new' in df_display_rules.columns:
                    try:
                        multiplier = 1 + (float(current_bulk_perc) / 100.0)
                        if multiplier < 0: multiplier = 0 
                        
                        # NADPISZ Bid_new, bazując na ORYGINALNYM Bid
                        df_display_rules['Bid_new'] = pd.to_numeric(df_display_rules['Bid'], errors='coerce').fillna(0) * multiplier
                        df_display_rules['Bid_new'] = df_display_rules['Bid_new'].round(2)
                    except Exception as e:
                        st.error(f"Wystąpił błąd podczas zmiany stawek: {e}")
                else:
                    st.error("Nie można zastosować zmiany - brak kolumny 'Bid' lub 'Bid_new' w danych.")
            # --- KONIEC ZMIANY ---

            # KROK 5: Zastosuj filtr podświetlenia (ten filtr tylko ukrywa wiersze, nie zmienia stawek)
            currency_symbol = 'PLN' if kraj == 'Polska' else 'EUR'
            summary_for_dropdown_df = pd.DataFrame(calculate_summary_row(df_display_rules, currency_symbol))

            highlight_rules = [r for r in st.session_state.rules if r.get('type') == 'Highlight' and r.get('name')]
            highlight_filter_options = {"Brak": None}
            for rule in highlight_rules:
                value_display = ""
                if rule['value_type'] == 'Średnia z konta':
                    if summary_for_dropdown_df is not None and rule['metric'] in summary_for_dropdown_df.columns:
                        avg_val = summary_for_dropdown_df.iloc[0][rule['metric']]
                        if rule['metric'] in ['ACOS', 'CTR', 'CR']: value_display = f"Średnia ({avg_val:.2%})"
                        else: value_display = f"Średnia ({avg_val:.2f})"
                    else: value_display = "Średnia z konta"
                else:
                    value_display = str(rule.get('value', ''))
                    if rule['metric'] in ['ACOS', 'CTR', 'CR']: value_display += "%"
                option_label = f"{rule['name']} ({rule['metric']} {rule['condition']} {value_display})"
                highlight_filter_options[option_label] = rule['name']
            
            with highlight_filter_placeholder.container():
                selected_label = st.selectbox("Filtruj wg podświetlenia:", list(highlight_filter_options.keys()))
            
            selected_rule_name = highlight_filter_options[selected_label]
            if selected_rule_name:
                selected_rule = next((r for r in highlight_rules if r['name'] == selected_rule_name), None)
                if selected_rule:
                    metric, condition_text = selected_rule['metric'], selected_rule['condition']
                    threshold = 0.0
                    if selected_rule['value_type'] == 'Średnia z konta':
                        if summary_for_dropdown_df is not None and metric in summary_for_dropdown_df.columns: threshold = summary_for_dropdown_df.iloc[0][metric]
                    else:
                        threshold = float(selected_rule.get('value', 0.0))
                        if metric in ['ACOS', 'CTR', 'CR']: threshold /= 100.0
                    
                    if condition_text == "Większe niż": df_display_rules = df_display_rules[df_display_rules[metric] > threshold]
                    elif condition_text == "Mniejsze niż": df_display_rules = df_display_rules[df_display_rules[metric] < threshold]
                    elif condition_text == "Równe": df_display_rules = df_display_rules[df_display_rules[metric] == threshold]

            if not df_display_rules.empty:
                cols_to_drop = [col for col in df_display_rules.columns if df_display_rules[col].isnull().all()]
                df_display_rules.drop(columns=cols_to_drop, inplace=True)
            if "_Campaign_Standardized" in df_display_rules.columns:
                df_display_rules.rename(columns={"_Campaign_Standardized": "Campaign"}, inplace=True)

            gb = GridOptionsBuilder.from_dataframe(df_display_rules)
            
            js_conditions = []
            condition_map_js = {"Większe niż": ">", "Mniejsze niż": "<", "Równe": "==="}
            color_map_hex = {"Zielony": "#d4edda", "Pomarańczowy": "#fff3cd", "Czerwony": "#f8d7da"}
            
            highlight_rules_df = pd.DataFrame([r for r in highlight_rules if r.get('name')])
            if not highlight_rules_df.empty:
                for rule_name, group in highlight_rules_df.groupby('name'):
                    group_js_conditions = []
                    highlight_col = group['highlight_column'].iloc[0]
                    color_hex = color_map_hex.get(group['color'].iloc[0], 'Czerwony')
                    for _, rule in group.iterrows():
                        metric = rule.get("metric")
                        op = condition_map_js.get(rule.get("condition"))
                        value = rule.get("value")
                        value_type = rule.get("value_type")
                        if not all([metric, op]): continue
                        js_condition_string_part = ""
                        if isinstance(metric, str) and 'x' in metric:
                            try:
                                parts = metric.lower().split('x')
                                multiplier = float(parts[0].replace(',', '.'))
                                source_col_name = parts[1].strip().capitalize()
                                target_col_name = str(value)
                                js_condition_string_part = (
                                    f" (params.data && typeof params.data['{source_col_name}'] === 'number' && "
                                    f"typeof params.data['{target_col_name}'] === 'number' && "
                                    f"({multiplier} * params.data['{source_col_name}'] {op} params.data['{target_col_name}'])) "
                                )
                            except (ValueError, IndexError): continue
                        else: 
                            final_comparison_value = None
                            is_numeric_comparison = True
                            if value_type == 'Średnia z konta':
                                if summary_for_dropdown_df is not None and metric in summary_for_dropdown_df.columns:
                                    final_comparison_value = summary_for_dropdown_df.iloc[0][metric]
                                else: continue
                            else:
                                final_comparison_value = value
                                if isinstance(final_comparison_value, str) and any(c.isalpha() for c in final_comparison_value):
                                    is_numeric_comparison = False
                            if is_numeric_comparison:
                                try:
                                    rule_value_conv = float(final_comparison_value)
                                    if math.isnan(rule_value_conv): continue
                                    if value_type == 'Wpisz wartość' and metric in ["ACOS", "CTR", "CR"]:
                                        rule_value_conv /= 100.0
                                    js_condition_string_part = f" (params.data && typeof params.data['{metric}'] === 'number' && params.data['{metric}'] {op} {rule_value_conv}) "
                                except (ValueError, TypeError): continue
                            else: 
                                column_to_compare = str(final_comparison_value)
                                js_condition_string_part = f" (params.data && typeof params.data['{metric}'] === 'number' && typeof params.data['{column_to_compare}'] === 'number' && params.data['{metric}'] {op} params.data['{column_to_compare}']) "
                        if js_condition_string_part: group_js_conditions.append(js_condition_string_part)
                    if group_js_conditions:
                        combined_condition = " && ".join(group_js_conditions)
                        js_conditions.append(f"if ({combined_condition} && params.colDef.field === '{highlight_col}') {{ style.backgroundColor = '{color_hex}'; }}")
            
            js_function_body = f"""
                if (!params.data) {{ return null; }}
                if (params.node.rowPinned) {{
                    return {{'fontWeight': 'bold', 'backgroundColor': '#f0f2f6'}};
                }}
                var style = {{}};
                {' '.join(js_conditions)}
                return style;
            """
            cell_style_jscode = JsCode(f"function(params) {{{js_function_body}}}")
            
            gb.configure_default_column(resizable=True, autoHeaderHeight=True, cellStyle=cell_style_jscode)
            
            for col in df_display_rules.columns:
                if col == "Kraj":
                     gb.configure_column(col, filter='agSetColumnFilter', pinned='left', width=120)
                else:
                     gb.configure_column(col, filter='agSetColumnFilter')
            
            if "Bid_new" in df_display_rules.columns: gb.configure_column("Bid_new", editable=True)

            currency_symbol = 'PLN' if kraj == 'Polska' else 'EUR'
            formatter_js_currency_simple = JsCode(f"""function(params){{if(params.value==null||isNaN(params.value))return'';return params.value.toLocaleString('pl-PL',{{style:'currency',currency:'{currency_symbol}',maximumFractionDigits:2}})}}""")
            
            for c in df_display_rules.columns:
                c_base = c.replace('_M', '')
                formatter_js = None
                if c_base in NUMERIC_COLS or c == "Campaign" or c == "Kraj":
                    if "ACOS" in c_base or "CTR" in c_base or "CR" in c_base: formatter_js=JsCode("""function(params){if(params.value==null||isNaN(params.value))return'';return params.value.toLocaleString('pl-PL',{style:'percent', minimumFractionDigits:2, maximumFractionDigits:2})}""")
                    elif any(x in c_base for x in["Price","Spend","Sales","Bid","CPC"]):
                        formatter_js = formatter_js_currency_simple
                    elif "ROAS" in c_base: formatter_js=JsCode("""function(params){if(params.value==null||isNaN(params.value))return'';return params.value.toLocaleString('pl-PL',{maximumFractionDigits:2})}""")
                    elif c != "Campaign" and c != "Kraj": formatter_js=JsCode("""function(params){if(params.value==null||isNaN(params.value))return'';return Math.round(params.value).toLocaleString('pl-PL')}""")
                    
                    if c != "Campaign" and c != "Kraj": 
                        gb.configure_column(c, type=["numericColumn","rightAligned"], valueFormatter=formatter_js)

            # Klucz siatki jest już zdefiniowany wyżej
            if 'current_grid_key' not in st.session_state or st.session_state.current_grid_key != grid_key:
                st.session_state.current_grid_key = grid_key
                st.session_state.pinned_row = calculate_summary_row(df_display_rules, currency_symbol)
                st.session_state.grid_state = {} 

            grid_options = gb.build()
            grid_options['pinnedBottomRowData'] = st.session_state.pinned_row
            
            grid_response = AgGrid(
                df_display_rules, gridOptions=grid_options, update_mode=GridUpdateMode.MODEL_CHANGED,
                height=600, allow_unsafe_jscode=True, theme='ag-theme-alpine',
                key=grid_key, enable_enterprise_modules=True
            )
            
            df_filtered = pd.DataFrame(grid_response['data'])
            newly_calculated_row = calculate_summary_row(df_filtered, currency_symbol)

            if newly_calculated_row != st.session_state.pinned_row:
                st.session_state.pinned_row = newly_calculated_row
                st.rerun()

            st.markdown("---")
            
            btn_cols = st.columns(3)
            
            with btn_cols[0]:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_filtered.to_excel(writer, index=False, sheet_name='DashboardExport')
                    workbook, worksheet = writer.book, writer.sheets['DashboardExport']
                    header = df_filtered.columns.values.tolist()
                    currency_format = workbook.add_format({'num_format': f'#,##0.00 "{currency_symbol}"'}); 
                    percent_format = workbook.add_format({'num_format': '0.00%'}); 
                    integer_format = workbook.add_format({'num_format': '#,##0'}); 
                    roas_format = workbook.add_format({'num_format': '#,##0.00'})
                    for idx, col_name in enumerate(header):
                        c_base = col_name.replace('_M', '')
                        if "ACOS" in c_base or "CTR" in c_base or "CR" in c_base: worksheet.set_column(idx, idx, 12, percent_format)
                        elif any(x in c_base for x in ["Price", "Spend", "Sales", "Bid", "CPC"]): worksheet.set_column(idx, idx, 15, currency_format)
                        elif "ROAS" in c_base: worksheet.set_column(idx, idx, 12, roas_format)
                        elif c_base in ["Orders", "Impressions", "Clicks", "Quantity", "Units"]: worksheet.set_column(idx, idx, 12, integer_format)
                    worksheet.autofit()
                
                st.download_button(
                    label="📥 Pobierz widok (Excel)", 
                    data=buffer, 
                    file_name=f"dashboard_view_{kraj}_{widok}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    help="Pobierz dane widoczne w tabeli jako plik Excel (do podglądu).",
                    use_container_width=True
                )

            with btn_cols[1]:
                is_disabled = (kraj == "Wszystko")
                help_text = "Generuje plik .xlsx gotowy do wgrania, zawierający tylko wiersze ze zmienionymi stawkami. Działa tylko dla pojedynczego kraju."
                if is_disabled:
                    help_text = "Ta funkcja jest niedostępna dla widoku 'Wszystko'. Wybierz pojedynczy kraj, aby wygenerować plik do wgrania."

                if st.button("📑 Pobierz PLIK DO WGRANIA", use_container_width=True, disabled=is_disabled, help=help_text):
                    if grid_response['data'] is not None:
                        current_grid_data = pd.DataFrame(grid_response['data'])
                        
                        bid_c = pd.to_numeric(current_grid_data['Bid'], errors='coerce').fillna(0)
                        bid_new_c = pd.to_numeric(current_grid_data['Bid_new'], errors='coerce').fillna(0)
                        changed_rows_df = current_grid_data[bid_c.round(2) != bid_new_c.round(2)].copy()

                        if changed_rows_df.empty:
                            st.warning("Brak zmienionych stawek do pobrania. Zmień wartości w 'Bid_new'.")
                        else:
                            try:
                                gid_key = {"Sponsored Products": "SP_TYDZIEN", "Sponsored Brands": "SB_TYDZIEN", "Sponsored Display": "SD_TYDZIEN"}.get(typ_kampanii)
                                gid = KRAJE_MAPA[kraj].get(gid_key)
                                tab_id = KRAJE_MAPA[kraj]["tab_id"]
                                
                                raw_df = pd.read_csv(get_url(tab_id, gid), dtype=str)
                                original_columns = raw_df.columns.tolist()
                                processed_raw_df = process_loaded_data(raw_df.copy(), typ_kampanii)

                                key_clean_names = ['Campaign']
                                if widok == 'Keyword': key_clean_names.extend(['Keyword text', 'Match type'])
                                elif widok in ['Product targeting', 'Audience targeting', 'Contextual targeting']: key_clean_names.append('Targeting expression')
                                elif widok == 'Product ad': key_clean_names.append('SKU')
                                elif widok == 'Auto keyword/ASIN': key_clean_names.append('Customer search term')
                                
                                rename_map_for_updates = {v: k for k,v in cols_map.items() if k in key_clean_names}
                                updates_renamed = changed_rows_df.rename(columns=rename_map_for_updates)
                                update_keys = [k for k in key_clean_names if k in updates_renamed.columns]
                                updates_for_merge = updates_renamed[update_keys + ['Bid_new']].copy()
                                
                                rename_for_merge = {k: cols_map.get(k) for k in update_keys}
                                updates_for_merge.rename(columns=rename_for_merge, inplace=True)
                                merge_on_cols = [cols_map.get(k) for k in update_keys]

                                for key in merge_on_cols:
                                    processed_raw_df[key] = processed_raw_df[key].astype(str).fillna('')
                                    updates_for_merge[key] = updates_for_merge[key].astype(str).fillna('')
                                
                                merged_df = pd.merge(processed_raw_df, updates_for_merge, on=merge_on_cols, how='left')
                                merged_df['Bid'] = merged_df['Bid_new'].fillna(merged_df['Bid'])
                                merged_df['Operation'] = np.where(merged_df['Bid_new'].notna(), 'Update', '')
                                
                                upload_file_df = merged_df[merged_df['Operation'] == 'Update'].copy()
                                
                                POTENTIAL_CAMPAIGN_COLS = ["Campaign name (Informational only)", "Campaign Name (Informational only)", "Campaign name", "Campaign Name", "Campaign"]
                                actual_campaign_col = find_first_existing_column(raw_df, POTENTIAL_CAMPAIGN_COLS)
                                if actual_campaign_col and '_Campaign_Standardized' in upload_file_df.columns:
                                    upload_file_df.rename(columns={'_Campaign_Standardized': actual_campaign_col}, inplace=True)
                                
                                final_columns_existing = [col for col in original_columns if col in upload_file_df.columns]
                                final_upload_df = upload_file_df[final_columns_existing]
                                
                                upload_buffer = io.BytesIO()
                                with pd.ExcelWriter(upload_buffer, engine='xlsxwriter') as writer:
                                    final_upload_df.to_excel(writer, index=False, sheet_name='Updated_Bids')
                                
                                st.session_state.download_upload_file = upload_buffer.getvalue()
                                st.success(f"Wygenerowano plik do wgrania z {len(final_upload_df)} zmianami. Pobieranie rozpocznie się za chwilę...")

                            except Exception as e:
                                st.error(f"Błąd podczas generowania pliku do wgrania: {e}")
                                
            if 'download_upload_file' in st.session_state and st.session_state.download_upload_file:
                st.download_button(
                    label="Pobierz plik (kliknij, jeśli nie pobrało się auto)",
                    data=st.session_state.download_upload_file,
                    file_name=f"upload_changes_{kraj}_{typ_kampanii}_{widok}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_upload_file_btn"
                )
                del st.session_state.download_upload_file 

            with btn_cols[2]:
                if st.button("✅ Zapisz zmiany do 'New Bid'", use_container_width=True, type="primary"):
                    if grid_response['data'] is not None:
                        updated_df = pd.DataFrame(grid_response['data'])
                        st.session_state.manual_bid_updates = { "data": updated_df, "widok": widok, "kraj": kraj, "typ_kampanii": typ_kampanii, "cols_map": cols_map }
                        st.success("Zmiany zapisane w pamięci! Przejdź do 'New Bid', aby wygenerować pełny plik.")
                    else:
                        st.warning("Brak danych w tabeli do zapisania.")
            
        else:
            st.warning("Brak danych dla wybranego okresu lub filtrów.")
# <--- KONIEC ZAKTUALIZOWANEJ ZAKŁADKI ---



# <--- POCZĄTEK ZAKTUALIZOWANEJ ZAKŁADKI "New Bid" (z wykluczeniami) ---
# PODMIEŃ CAŁY BLOK 'with tab2:' W SWOIM KODZIE
with tab2:
    st.header("Automatycznie zaktualizowany plik z nowymi stawkami")
    st.info("Dane w tej tabeli są aktualizowane automatycznie na podstawie globalnie wybranego konta. Najpierw stosowane są reguły (zgodnie z priorytetem), a następnie nakładane są zapisane zmiany z Dashboardu.")
    
    konto_nb = st.session_state.selected_account
    KRAJE_MAPA_NB = ACCOUNTS_DATA[konto_nb]
    st.write(f"#### Dane dla konta: **{konto_nb}**")

    nb_cols = st.columns(2)
    with nb_cols[0]:
        kraj_nb = st.selectbox("Kraj", list(KRAJE_MAPA_NB.keys()), key="newbid_kraj_4")
    with nb_cols[1]:
        typ_kampanii_nb = st.selectbox("Typ kampanii", ["Sponsored Products", "Sponsored Brands", "Sponsored Display"], key="newbid_typ_4")
    
    # --- NOWY BLOK: Wykluczenia ---
    st.markdown("##### Wykluczenia")
    exclusions_text = st.text_area(
        "Wklej DOKŁADNE nazwy kampanii do wykluczenia (oddzielone przecinkiem):",
        placeholder="Kampania A, Kampania B, Dokładna Nazwa Kampanii C...",
        key=f"newbid_exclusions_{konto_nb}_{kraj_nb}_{typ_kampanii_nb}",
        help="Wszystkie wiersze pasujące DOKŁADNIE do tych nazw zostaną usunięte z finalnego pliku do pobrania."
    )
    # --- KONIEC NOWEGO BLOKU ---

    state_key = f"{konto_nb}_{kraj_nb}_{typ_kampanii_nb}"
    
    gid_key = {"Sponsored Products": "SP_TYDZIEN", "Sponsored Brands": "SB_TYDZIEN", "Sponsored Display": "SD_TYDZIEN"}.get(typ_kampanii_nb)
    
    gid = KRAJE_MAPA_NB[kraj_nb].get(gid_key)
    tab_id = KRAJE_MAPA_NB[kraj_nb]["tab_id"]

    if gid and tab_id:
        try:
            with st.spinner("Przetwarzanie danych..."):
                base_df_raw = pd.read_csv(get_url(tab_id, gid), dtype=str)
                original_columns = base_df_raw.columns.tolist()

                base_df_processed = process_loaded_data(base_df_raw.copy(), typ_kampanii_nb)

                df_with_rules, num_rules_applied = apply_rules_to_bids_vectorized(base_df_processed, st.session_state.rules)
                st.success(f"Krok 1: Zastosowano reguły automatyczne, zmieniając {num_rules_applied} stawek.")
                
                final_df_processed = df_with_rules
                updates = st.session_state.get('manual_bid_updates')

                # Sprawdź, czy zapisane zmiany pasują (logika bez zmian)
                # --- ZMIANA: Sprawdzamy też, czy zapisane zmiany nie są z "Wszystko" ---
                if (updates and 
                    (updates['kraj'] == kraj_nb or updates['kraj'] == "Wszystko") and 
                    updates['typ_kampanii'] == typ_kampanii_nb):
                # --- KONIEC ZMIANY ---

                    updates_df = updates['data']
                    source_cols_map = updates.get("cols_map", {})
                    widok_source = updates['widok']
                    
                    key_clean_names = ['Campaign']
                    # --- ZMIANA: Dodajemy 'Kraj' jako klucz, jeśli zapis był z "Wszystko" ---
                    if updates['kraj'] == "Wszystko":
                        key_clean_names.append('Kraj')
                    # --- KONIEC ZMIANY ---

                    if widok_source == 'Keyword': key_clean_names.extend(['Keyword text', 'Match type'])
                    elif widok_source in ['Product targeting', 'Audience targeting', 'Contextual targeting']: key_clean_names.append('Targeting expression')
                    elif widok_source == 'Product ad': key_clean_names.append('SKU')
                    elif widok_source == 'Auto keyword/ASIN': key_clean_names.append('Customer search term')
                    
                    target_keys_source = [source_cols_map.get(k) for k in key_clean_names if source_cols_map.get(k)]
                    
                    if target_keys_source and 'Bid_new' in updates_df.columns:
                        
                        rename_map_for_updates = {v: k for k,v in source_cols_map.items() if k in key_clean_names}
                        updates_renamed = updates_df.rename(columns=rename_map_for_updates)

                        update_keys = [k for k in key_clean_names if k in updates_renamed.columns]
                        
                        if all(source_cols_map.get(k) in final_df_processed.columns for k in update_keys):
                            merge_on_cols = [source_cols_map.get(k) for k in update_keys]
                            
                            updates_for_merge = updates_renamed[update_keys + ['Bid_new']].copy()
                            updates_for_merge.rename(columns={'Bid_new': 'Bid_new_manual'}, inplace=True)
                            updates_for_merge['Bid_new_manual'] = pd.to_numeric(updates_for_merge['Bid_new_manual'], errors='coerce')
                            updates_for_merge.dropna(subset=['Bid_new_manual'], inplace=True)
                            
                            rename_for_merge = {k: source_cols_map.get(k) for k in update_keys}
                            updates_for_merge.rename(columns=rename_for_merge, inplace=True)
                            
                            for key in merge_on_cols:
                                final_df_processed[key] = final_df_processed[key].astype(str).fillna('')
                                updates_for_merge[key] = updates_for_merge[key].astype(str).fillna('')
                            
                            merged_df = pd.merge(final_df_processed, updates_for_merge, on=merge_on_cols, how='left')
                            merged_df['Bid_new'] = merged_df['Bid_new_manual'].fillna(merged_df['Bid_new'])
                            final_df_processed = merged_df.drop(columns=['Bid_new_manual'])
                            st.success(f"Krok 2: Pomyślnie nałożono {len(updates_for_merge)} ręcznych zmian z Dashboardu.")
                
                # Ustaw 'Bid' na nową wartość (bez zmian)
                final_df_processed['Bid'] = final_df_processed['Bid_new']
                final_df_processed['Bid'] = final_df_processed['Bid'].apply(lambda x: '' if pd.isna(x) else str(x))

                if 'Operation' not in final_df_processed.columns:
                    final_df_processed['Operation'] = ''
                final_df_processed['Operation'] = np.where(final_df_processed['Bid'].astype(str).str.strip().ne(''), 'Update', '')
                if 'Operation' not in original_columns:
                    original_columns.append('Operation')
                
                # Znajdź kolumnę kampanii (bez zmian)
                POTENTIAL_CAMPAIGN_COLS = ["Campaign name (Informational only)", "Campaign Name (Informational only)", "Campaign name", "Campaign Name", "Campaign"]
                actual_campaign_col = find_first_existing_column(base_df_raw, POTENTIAL_CAMPAIGN_COLS)
                if actual_campaign_col and '_Campaign_Standardized' in final_df_processed.columns:
                    final_df_processed.rename(columns={'_Campaign_Standardized': actual_campaign_col}, inplace=True)
                
                # --- NOWY BLOK: Zastosowanie wykluczeń ---
                final_df_for_download = final_df_processed.copy()
                
                if exclusions_text:
                    # 1. Pobierz listę wykluczeń
                    excluded_campaigns = [name.strip().lower() for name in exclusions_text.split(',') if name.strip()]
                    
                    if excluded_campaigns and actual_campaign_col in final_df_for_download.columns:
                        # 2. Stwórz maskę do wykluczenia (isin sprawdza DOKŁADNE dopasowania)
                        exclusion_mask = final_df_for_download[actual_campaign_col].astype(str).str.lower().isin(excluded_campaigns)
                        
                        # 3. Odwróć maskę (chcemy zatrzymać wszystko, co NIE jest na liście)
                        final_df_for_download = final_df_for_download[~exclusion_mask]
                        
                        st.warning(f"Zastosowano wykluczenia. Usunięto {exclusion_mask.sum()} wierszy pasujących do {len(excluded_campaigns)} nazw kampanii.")
                    elif not actual_campaign_col:
                        st.error("Nie można zastosować wykluczeń: Nie znaleziono kolumny kampanii w pliku.")
                # --- KONIEC NOWEGO BLOKU ---
                
                final_columns_existing = [col for col in original_columns if col in final_df_for_download.columns]
                final_df_for_download = final_df_for_download[final_columns_existing]
                
                # Zapisz przefiltrowane dane do stanu sesji
                st.session_state.new_bid_data[state_key] = final_df_for_download
        
        except Exception as e:
            st.error(f"Wystąpił błąd podczas przetwarzania pliku New Bid: {e}")
            
    # Wyświetlanie danych (bez zmian)
    if state_key in st.session_state.new_bid_data:
        display_df = st.session_state.new_bid_data[state_key]
        
        # Pokaż tylko wiersze ze zmianami, aby było czytelniej
        display_df_changes_only = display_df[display_df['Operation'] == 'Update'].copy()
        
        if display_df_changes_only.empty:
            st.info("Nie znaleziono żadnych automatycznych ani ręcznych zmian stawek dla tego widoku.")
        else:
            st.markdown(f"**Znaleziono {len(display_df_changes_only)} wierszy ze zmianami (po wykluczeniach):**")
            # Użyj st.dataframe do szybkiego podglądu, a nie AgGrid
            st.dataframe(display_df_changes_only, use_container_width=True, hide_index=True)
        
        # Przycisk pobierania zawsze używa pełnego DataFrame (w tym wierszy bez zmian, ale po wykluczeniach)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Updated_Bids')
        
        st.download_button(
            label=f"📥 Pobierz plik z nowymi stawkami ({len(display_df)} wierszy)", 
            data=buffer.getvalue(), 
            file_name=f"NewBids_{kraj_nb}_{typ_kampanii_nb}.xlsx", 
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
# <--- KONIEC ZAKTUALIZOWANEJ ZAKŁADKI "New Bid" ---


with tab3:
    st.header("Wyszukiwarka Produktów")
    selected_account = st.session_state.selected_account
    st.info(f"Wyszukiwanie produktów dla konta: **{selected_account}**")
    search_df = load_search_data()
    if search_df.empty:
        st.error("Nie udało się załadować danych o produktach. Sprawdź komunikaty o błędach (jeśli są) i upewnij się, że arkusze Google są poprawnie udostępnione.")
    else:
        account_df = search_df[search_df['Account'] == selected_account].copy()
        if account_df.empty:
            st.warning(f"Brak danych produktowych do przeszukania dla konta {selected_account}.")
        else:
            search_term = st.text_input("Wpisz SKU, ASIN, nazwę produktu (można wiele po przecinku) i naciśnij Enter:", key=f"{selected_account}_search")
            if search_term:
                search_list = [term.strip().lower() for term in search_term.split(',') if term.strip()]
                if search_list:
                    combined_mask = pd.Series([False] * len(account_df), index=account_df.index)
                    
                    search_cols = ['SKU', 'Nazwa produktu', 'ASIN']
                    existing_search_cols = [c for c in search_cols if c in account_df.columns]
                    
                    for term in search_list:
                        term_mask = pd.Series([False] * len(account_df), index=account_df.index)
                        for col in existing_search_cols:
                            term_mask = term_mask | account_df[col].str.lower().str.contains(term, na=False)
                        combined_mask = combined_mask | term_mask
                    
                    results_df = account_df[combined_mask]
                    if not results_df.empty:
                        display_cols = ['Account', 'SKU', 'ASIN', 'Nazwa produktu', 'Campaign', 'Campaign Type', 'Targeting Type', 'Country']
                        display_cols_exist = [col for col in display_cols if col in results_df.columns]
                        display_df = results_df[display_cols_exist].drop_duplicates().sort_values(by=['SKU', 'Country', 'Campaign'])
                        st.markdown(f"--- \n**Znaleziono {len(display_df)} unikalnych wyników dla:** `{', '.join(search_list)}`")
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            display_df.to_excel(writer, index=False, sheet_name='SearchResults')
                            writer.sheets['SearchResults'].autofit()
                        st.download_button(label="📥 Pobierz wyniki do Excela", data=buffer, file_name=f"product_search_results_{selected_account}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        gb = GridOptionsBuilder.from_dataframe(display_df)
                        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
                        AgGrid(display_df, gridOptions=gb.build(), height=600, width='100%', allow_unsafe_jscode=True, theme='ag-theme-streamlit')
                    else:
                        st.warning(f"Nie znaleziono żadnych produktów pasujących do: '{', '.join(search_list)}' w koncie {selected_account}.")
            else:
                st.info(f"Wpisz SKU, ASIN lub nazwę, aby rozpocząć wyszukiwanie w koncie {selected_account}.")


with tab4:
    st.header("📜 Konfiguracja Reguł Optymalizacji")
    st.info("""
    Zarządzaj regułami do automatycznej zmiany stawek (Bid) lub wizualnego wyróżniania komórek (Highlight).
    **Priorytet reguły "Bid" zależy od jej kolejności w tabeli.** Reguły "Highlight" działają niezależnie.
    
    Możesz również **zaimportować reguły z pliku** Excel lub CSV. Ich kolejność w pliku będzie odzwierciedlać ich priorytet.
    
    Pola nieużywane dla danego typu reguły są automatycznie wyszarzane.
    Po zakończeniu edycji kliknij przycisk **'Zapisz zmiany'**, aby trwale je zastosować.
    """)
    
    rules_df = pd.DataFrame(st.session_state.rules)
    cols_order = ['type', 'name', 'metric', 'condition', 'value_type', 'value', 'change', 'color', 'highlight_column']
    
    if not rules_df.empty:
        display_cols = [col for col in cols_order if col in rules_df.columns]
        rules_df = rules_df[display_cols]
    else:
        rules_df = pd.DataFrame(columns=cols_order)

    js_editable_if_highlight = JsCode("function(params) { return params.data.type === 'Highlight'; }")
    js_style_if_bid = JsCode("function(params) { if(params.data.type === 'Bid') return {'backgroundColor': '#f0f0f0', 'color': '#6c757d'}; return null; }")
    js_formatter_dash_if_bid = JsCode("function(params) { return params.data.type === 'Bid' ? '-' : params.value; }")
    js_editable_if_bid = JsCode("function(params) { return params.data.type === 'Bid'; }")
    js_style_if_highlight = JsCode("function(params) { if(params.data.type === 'Highlight') return {'backgroundColor': '#f0f0f0', 'color': '#6c757d'}; return null; }")
    js_change_formatter = JsCode("""
        function(params) {
            if (params.data.type === 'Highlight') { return '-'; }
            if (params.value == null || isNaN(params.value)) { return ''; }
            return params.value.toFixed(2) + '%';
        }
    """)

    gb = GridOptionsBuilder.from_dataframe(rules_df)
    gb.configure_default_column(editable=True, resizable=True, autoHeaderHeight=True, wrapText=True)
    gb.configure_column("type", header_name="Typ reguły", width=140, cellEditor='agSelectCellEditor', cellEditorParams={'values': ["Bid", "Highlight"]})
    gb.configure_column("name", header_name="Nazwa reguły", width=200, headerTooltip="Wszystkie wiersze o tej samej nazwie należą do jednej reguły 'Bid'")
    
    metrics_list = ["ACOS", "ROAS", "CTR", "CR", "Spend", "Sales", "Orders", "Impressions", "Clicks", "CPC", "0.75xPrice"]
    gb.configure_column("metric", header_name="Wskaźnik", width=150, cellEditor='agSelectCellEditor', cellEditorParams={'values': metrics_list})
    
    condition_list = ['Większe niż', 'Mniejsze niż', 'Równe']
    gb.configure_column("condition", header_name="Warunek", width=150, cellEditor='agSelectCellEditor', cellEditorParams={'values': condition_list})
    gb.configure_column("value_type", header_name="Typ wartości", width=180, cellEditor='agSelectCellEditor', cellEditorParams={'values': ["Wpisz wartość", "Średnia z konta"]}, editable=js_editable_if_highlight, cellStyle=js_style_if_bid, valueFormatter=js_formatter_dash_if_bid)

    js_value_editable = JsCode("function(params) { return params.data.value_type === 'Wpisz wartość'; }")
    js_value_style = JsCode("function(params) { if (params.data.value_type !== 'Wpisz wartość') return { 'backgroundColor': '#f0f0f0', 'color': '#6c757d', 'fontStyle': 'italic' }; return null; }")
    
    js_value_formatter = JsCode("""
        function(params) {
            if (params.value == null) { return ''; }
            if (isNaN(params.value)) { return params.value; }
            const percentMetrics = ['ACOS', 'CTR', 'CR'];
            if (params.data && percentMetrics.includes(params.data.metric)) {
                return params.value.toFixed(2) + '%';
            }
            return params.value.toLocaleString('pl-PL', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
    """)
    js_value_parser = JsCode("function(params) { let v = params.newValue; if (typeof v === 'string') { v = v.replace('%', '').trim().replace(',', '.'); } let num = Number(v); return isNaN(num) ? params.newValue.trim() : num; }")
    gb.configure_column("value", header_name="Wartość", width=120, editable=js_value_editable, cellStyle=js_value_style, valueFormatter=js_value_formatter, valueParser=js_value_parser, headerTooltip="Wpisz liczbę (np. 17,5) lub nazwę kolumny (np. Price).")
    gb.configure_column("change", header_name="Zmiana %", width=120, type=["numericColumn"], editable=js_editable_if_bid, cellStyle=js_style_if_highlight, valueFormatter=js_change_formatter, headerTooltip="Aktywne tylko dla reguł typu 'Bid'")
    color_options = ["Czerwony", "Pomarańczowy", "Zielony"]
    gb.configure_column("color", header_name="Kolor", width=150, cellEditor='agSelectCellEditor', cellEditorParams={'values': color_options}, editable=js_editable_if_highlight, cellStyle=js_style_if_bid, valueFormatter=js_formatter_dash_if_bid, headerTooltip="Aktywne tylko dla reguł typu 'Highlight'")
    
    highlightable_columns = ["Campaign", "Match type", "Keyword text", "Targeting expression", "SKU", "Spend", "Sales", "Orders", "ACOS", "ROAS", "CTR", "CR", "Bid", "Bid_new", "Price"]
    gb.configure_column("highlight_column", header_name="Kolumna do podświetlenia", width=200, cellEditor='agSelectCellEditor', cellEditorParams={'values': highlightable_columns}, editable=js_editable_if_highlight, cellStyle=js_style_if_bid, headerTooltip="Aktywne tylko dla reguł typu 'Highlight'")

    gb.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(rules_df, gridOptions=grid_options, height=400, width='100%', update_mode=GridUpdateMode.MANUAL, allow_unsafe_jscode=True, theme='ag-theme-streamlit', key='rules_grid_final_no_priority')
    
    st.markdown("---")
    st.subheader("Import/Eksport Reguł")
    import_export_cols = st.columns([3, 1.5, 1.5]) 
    with import_export_cols[0]:
        uploaded_file = st.file_uploader("Wybierz plik Excel (.xlsx) lub CSV (.csv) do importu", type=['xlsx', 'csv'], label_visibility="collapsed")

    with import_export_cols[1]:
        if st.button("⬆️ Załaduj z pliku", use_container_width=True):
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.xlsx'):
                        df_upload = pd.read_excel(uploaded_file, engine='openpyxl')
                    else:
                        try:
                            uploaded_file.seek(0)
                            df_upload = pd.read_csv(uploaded_file, sep=';')
                            if df_upload.shape[1] < 2: raise ValueError("Niepoprawny separator")
                        except (Exception, pd.errors.ParserError):
                            uploaded_file.seek(0)
                            df_upload = pd.read_csv(uploaded_file, sep=',')
                    
                    final_rules_df = df_upload.copy()
                    if 'name' not in final_rules_df.columns:
                        st.error("Błąd importu: Plik musi zawierać kolumnę 'name'.")
                    else:
                        if 'Priorytet' in final_rules_df.columns: final_rules_df.drop(columns=['Priorytet'], inplace=True)
                        if 'priority' in final_rules_df.columns: final_rules_df.drop(columns=['priority'], inplace=True)

                        for col in ['value', 'change']:
                            if col in final_rules_df.columns:
                                if col == 'value':
                                    final_rules_df['temp_value'] = pd.to_numeric(final_rules_df['value'].astype(str).str.replace(',', '.'), errors='coerce')
                                    final_rules_df['value'] = np.where(final_rules_df['temp_value'].notna(), final_rules_df['temp_value'], final_rules_df['value'])
                                    final_rules_df.drop(columns=['temp_value'], inplace=True)
                                else:
                                    final_rules_df[col] = final_rules_df[col].astype(str).str.replace(',', '.').str.strip()
                                    final_rules_df[col] = pd.to_numeric(final_rules_df[col], errors='coerce').fillna(0.0)
                        
                        bid_mask = final_rules_df['type'] == 'Bid'
                        final_rules_df.loc[bid_mask, 'value_type'] = 'Wpisz wartość'
                        final_rules_df.loc[bid_mask, 'color'] = 'Czerwony'
                        
                        highlight_mask = final_rules_df['type'] == 'Highlight'
                        final_rules_df.loc[highlight_mask, 'change'] = 0.0
                        final_rules_df.loc[highlight_mask, 'highlight_column'] = final_rules_df.loc[highlight_mask, 'highlight_column'].fillna(final_rules_df.loc[highlight_mask, 'metric'])

                        avg_mask = final_rules_df['value_type'] == 'Średnia z konta'
                        final_rules_df.loc[avg_mask, 'value'] = 0.0
                        
                        expected_keys = ['type', 'name', 'metric', 'condition', 'value_type', 'value', 'change', 'color', 'highlight_column']
                        for key in expected_keys:
                            if key not in final_rules_df.columns:
                                final_rules_df[key] = '' 

                        st.session_state.rules = final_rules_df.to_dict('records')
                        save_rules_to_file(st.session_state.rules)
                        st.toast("Reguły zostały pomyślnie zaimportowane!", icon="⬆️")
                        st.rerun()
                except Exception as e:
                    st.error(f"Wystąpił błąd podczas importowania pliku: {e}")
            else:
                st.warning("Najpierw wybierz plik do załadowania.")

    with import_export_cols[2]:
        buffer = io.BytesIO()
        df_to_download = pd.DataFrame(grid_response['data'])
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_to_download.to_excel(writer, index=False, sheet_name='Reguly')
            writer.sheets['Reguly'].autofit()
        
        st.download_button(label="📥 Pobierz reguły (Excel)", data=buffer, file_name="konfiguracja_regul.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown("---")
    st.subheader("Edycja Reguł")
    action_cols = st.columns([1, 1, 1, 1.5])
    
    if action_cols[3].button("✅ Zapisz zmiany", use_container_width=True, type="primary"):
        updated_df = pd.DataFrame(grid_response['data'])
        
        if not updated_df.empty:
            bid_mask = updated_df['type'] == 'Bid'
            updated_df.loc[bid_mask, 'value_type'] = 'Wpisz wartość'
            updated_df.loc[bid_mask, 'color'] = 'Czerwony'
            updated_df.loc[bid_mask, 'highlight_column'] = ''
            
            highlight_mask = updated_df['type'] == 'Highlight'
            updated_df.loc[highlight_mask, 'change'] = 0.0
            updated_df.loc[highlight_mask, 'highlight_column'] = updated_df.loc[highlight_mask, 'highlight_column'].fillna(updated_df.loc[highlight_mask, 'metric'])
            
            avg_mask = updated_df['value_type'] == 'Średnia z konta'
            updated_df.loc[avg_mask, 'value'] = 0.0
        
        st.session_state.rules = updated_df.to_dict('records')
        save_rules_to_file(st.session_state.rules)
        st.toast("Zmiany w regułach zostały zapisane!", icon="✔️")
        st.rerun()

    with action_cols[0]:
        num_to_add = st.number_input("Liczba wierszy do dodania:", min_value=1, value=1, step=1, label_visibility="collapsed")
    with action_cols[1]:
        if st.button(f"➕ Dodaj", use_container_width=True, help=f"Dodaj {num_to_add} nowy(ch) wiersz(y) na końcu tabeli"):
            for i in range(num_to_add):
                new_rule = {"type":"Bid", "name": "", "metric": "ACOS", "condition": "Większe niż", "value": 0.0, "change": 0.0, "value_type": "Wpisz wartość", "color": "Czerwony", "highlight_column": "ACOS"}
                st.session_state.rules.append(new_rule)
            save_rules_to_file(st.session_state.rules)
            st.rerun()
            
    with action_cols[2]:
        if st.button("🗑️ Usuń", use_container_width=True, help="Usuń zaznaczone wiersze"):
            selected = grid_response['selected_rows']
            if selected:
                selected_indices = [row['_selectedRowNodeInfo']['nodeRowIndex'] for row in selected]
                current_rules_df = pd.DataFrame(st.session_state.rules)
                df_after_delete = current_rules_df.drop(selected_indices).reset_index(drop=True)
                st.session_state.rules = df_after_delete.to_dict('records')
                save_rules_to_file(st.session_state.rules)
                st.rerun()
            else:
                st.warning("Nie zaznaczono żadnych wierszy do usunięcia.")


# <--- POCZĄTEK ZAKTUALIZOWANEJ ZAKŁADKI ID ACOS (z filtrami ACOS/TACOS) ---
# <--- POCZĄTEK ZAKTUALIZOWANEJ ZAKŁADKI ID ACOS (z opcją "Wszystko") ---
# PODMIEŃ CAŁY BLOK 'with tab5:' W SWOIM KODZIE
with tab5:
    st.header("🎯 Analiza ACOS per ID (SKU)")

    # --- FUNKCJA DO PODSUMOWANIA (bez zmian) ---
    def calculate_acos_summary_row(df):
        """Oblicza wiersz podsumowania dla tabeli ACOS."""
        if df.empty:
            return None

        try:
            numeric_cols_to_sum = ['Total Spend', 'Total Sales', 'Total Sales (Total)', 'Total Orders (Total)']
            existing_numeric_cols = [col for col in numeric_cols_to_sum if col in df.columns]
            sums = df[existing_numeric_cols].sum()

            total_spend_sum = sums.get('Total Spend', 0)
            total_sales_sum = sums.get('Total Sales', 0)
            total_sales_total_sum = sums.get('Total Sales (Total)', 0)
            total_orders_total_sum = sums.get('Total Orders (Total)', 0)

            acos_summary = (total_spend_sum / total_sales_sum) if total_sales_sum > 0 else 0
            tacos_summary = (total_spend_sum / total_sales_total_sum) if total_sales_total_sum > 0 else 0

            summary_data = {
                'ID': 'SUMA',
                'nazwa': '',
                'marka': '',
                'kategoria': '',
                'Total Spend': total_spend_sum,
                'Total Sales': total_sales_sum,
                'ACOS': acos_summary,
                'Total Sales (Total)': total_sales_total_sum,
                'Total Orders (Total)': total_orders_total_sum,
                'TACOS': tacos_summary
            }
            return [summary_data] 
        except KeyError as e:
            st.warning(f"Brak kolumny do podsumowania: {e}. Wiersz sumy nie będzie wyświetlony.")
            return None
        except Exception as e:
            st.error(f"Błąd podczas obliczania sumy: {e}")
            return None
    # --- KONIEC FUNKCJI PODSUMOWANIA ---

    # Pobranie aktywnego konta
    konto_acos = st.session_state.selected_account
    KRAJE_MAPA_ACOS = ACCOUNTS_DATA[konto_acos]

    st.info(f"Analiza dla konta: **{konto_acos}**. Wybierz kraj (lub 'Wszystko'), aby zobaczyć zagregowane dane dla każdego SKU. Suma na dole tabeli aktualizuje się dynamicznie.")

    # --- FILTRY: Kraj i Okres ---
    filter_cols = st.columns(2)
    with filter_cols[0]:
        # --- ZMIANA: Dodanie opcji "Wszystko" ---
        kraje_lista = ["Wszystko"] + list(KRAJE_MAPA_ACOS.keys())
        kraj_acos = st.selectbox("Wybierz kraj", kraje_lista, key="acos_kraj_selector")
        # --- KONIEC ZMIANY ---
    with filter_cols[1]:
        okres_acos = st.radio("Przedział czasowy:", ["Tydzień", "Miesiąc"], key="acos_okres_selector", horizontal=True)

    # Klucz unikalny dla tej kombinacji filtrów
    grid_key_acos = f"acos_grid_{konto_acos}_{kraj_acos}_{okres_acos}"

    with st.spinner(f"Agregowanie danych dla {kraj_acos} (Okres: {okres_acos})..."):
        
        # --- ZMIANA: Logika ładowania danych dla "Wszystko" ---
        if kraj_acos == "Wszystko":
            all_dfs = []
            countries_to_load = list(KRAJE_MAPA_ACOS.keys()) # Załaduj wszystkie kraje zdefiniowane na koncie
            
            for country in countries_to_load:
                df_country = load_and_aggregate_by_sku(konto_acos, country, okres_acos)
                if not df_country.empty:
                    all_dfs.append(df_country)
            
            if all_dfs:
                # Połącz wszystkie ramki danych
                combined_df = pd.concat(all_dfs, ignore_index=True)
                
                # Przeprowadź drugą agregację, aby zsumować dane dla tego samego ID z różnych krajów
                numeric_cols = ['Total Spend', 'Total Sales', 'Total Sales (Total)', 'Total Orders (Total)']
                
                # Upewnij się, że wszystkie kolumny istnieją przed agregacją
                existing_numeric = [col for col in numeric_cols if col in combined_df.columns]
                
                if 'ID' in combined_df.columns and existing_numeric:
                    agg_rules = {col: 'sum' for col in existing_numeric}
                    agg_rules['nazwa'] = 'first'
                    agg_rules['marka'] = 'first'
                    agg_rules['kategoria'] = 'first'

                    # Usuń nieistniejące kolumny z zasad agregacji
                    final_agg_rules = {k: v for k, v in agg_rules.items() if k in combined_df.columns}

                    acos_df = combined_df.groupby('ID').agg(final_agg_rules).reset_index()

                    # Przelicz ACOS i TACOS na podstawie globalnych sum
                    acos_df['ACOS'] = np.where(
                        acos_df['Total Sales'] > 0,
                        acos_df['Total Spend'] / acos_df['Total Sales'],
                        0
                    )
                    acos_df['TACOS'] = np.where(
                        acos_df['Total Sales (Total)'] > 0,
                        acos_df['Total Spend'] / acos_df['Total Sales (Total)'],
                        0
                    )
                    
                    # Ustawienie kolejności kolumn
                    final_cols = ['ID', 'nazwa', 'marka', 'kategoria', 'Total Spend', 'Total Sales', 'ACOS', 'Total Sales (Total)', 'Total Orders (Total)', 'TACOS']
                    existing_final_cols = [col for col in final_cols if col in acos_df.columns]
                    acos_df = acos_df[existing_final_cols]
                else:
                    acos_df = pd.DataFrame() # Pusta ramka, jeśli brakuje ID lub kolumn numerycznych
            else:
                acos_df = pd.DataFrame() # Pusta ramka, jeśli nie załadowano żadnych danych
        else:
            # Oryginalna logika dla pojedynczego kraju
            acos_df = load_and_aggregate_by_sku(konto_acos, kraj_acos, okres_acos)
        # --- KONIEC ZMIANY ---

        if acos_df.empty:
            st.warning(f"Brak danych (SKU, Spend, Sales) do zagregowania dla konta {konto_acos}, kraju '{kraj_acos}' i okresu '{okres_acos}'.")
        else:
            st.markdown(f"### Znaleziono **{len(acos_df)}** unikalnych ID (SKU) dla **{kraj_acos}** (Okres: {okres_acos})")

            # --- FILTRY ACOS / TACOS (bez zmian) ---
            st.markdown("---")
            st.markdown("<h4 style='font-weight: 600; color: #333; margin-bottom: 10px;'>Filtrowanie tabeli</h4>", unsafe_allow_html=True)
            
            filter_cols_acos_main = st.columns(2)
            
            with filter_cols_acos_main[0]:
                f_acos_cols = st.columns([1, 1.5, 1.4]) 
                f_acos_cols[0].markdown("<p class='filter-label' style='text-align: left; margin-top: 8px;'>ACOS</p>", unsafe_allow_html=True)
                acos_op = f_acos_cols[1].selectbox("ACOS Op", ["Brak", ">", "<", "="], key="acos_tab_op", label_visibility="collapsed")
                acos_val_str = f_acos_cols[2].text_input("ACOS Val", key="acos_tab_val", placeholder="Wpisz wartość %", label_visibility="collapsed")

            with filter_cols_acos_main[1]:
                f_tacos_cols = st.columns([1, 1.5, 1.4]) 
                f_tacos_cols[0].markdown("<p class='filter-label' style='text-align: left; margin-top: 8px;'>TACOS</p>", unsafe_allow_html=True)
                tacos_op = f_tacos_cols[1].selectbox("TACOS Op", ["Brak", ">", "<", "="], key="tacos_tab_op", label_visibility="collapsed")
                tacos_val_str = f_tacos_cols[2].text_input("TACOS Val", key="tacos_tab_val", placeholder="Wpisz wartość %", label_visibility="collapsed")
            
            st.markdown("---") 

            # Zastosuj filtrowanie do acos_df *PRZED* przekazaniem do AgGrid
            if acos_op != "Brak" and acos_val_str:
                try:
                    val = float(acos_val_str.replace(',', '.')) / 100.0 
                    if 'ACOS' in acos_df.columns:
                        if acos_op == ">":
                            acos_df = acos_df[acos_df['ACOS'] > val]
                        elif acos_op == "<":
                            acos_df = acos_df[acos_df['ACOS'] < val]
                        elif acos_op == "=":
                            acos_df = acos_df[np.isclose(acos_df['ACOS'], val)]
                    else:
                        st.warning("Kolumna 'ACOS' nie jest dostępna do filtrowania.")
                except (ValueError, TypeError):
                    st.warning(f"Niepoprawna wartość dla ACOS: '{acos_val_str}'. Wpisz liczbę.")
            
            if tacos_op != "Brak" and tacos_val_str:
                try:
                    val = float(tacos_val_str.replace(',', '.')) / 100.0
                    if 'TACOS' in acos_df.columns:
                        if tacos_op == ">":
                            acos_df = acos_df[acos_df['TACOS'] > val]
                        elif tacos_op == "<":
                            acos_df = acos_df[acos_df['TACOS'] < val]
                        elif tacos_op == "=":
                            acos_df = acos_df[np.isclose(acos_df['TACOS'], val)]
                    else:
                        st.warning("Kolumna 'TACOS' nie jest dostępna do filtrowania.")
                except (ValueError, TypeError):
                    st.warning(f"Niepoprawna wartość dla TACOS: '{tacos_val_str}'. Wpisz liczbę.")
            # --- KONIEC FILTRÓW ---

            gb_acos = GridOptionsBuilder.from_dataframe(acos_df) 
            # --- ZMIANA: Waluta dla "Wszystko" ---
            # Jeśli Polska jest jedynym krajem, użyj PLN. W przeciwnym razie (w tym dla "Wszystko") użyj EUR.
            currency_symbol = 'PLN' if kraj_acos == 'Polska' else 'EUR'
            # --- KONIEC ZMIANY ---

            # Formattery JS (bez zmian)
            formatter_js_currency = JsCode(f"""function(params){{if(params.value==null||isNaN(params.value))return'';return params.value.toLocaleString('pl-PL',{{style:'currency',currency:'{currency_symbol}',maximumFractionDigits:2}})}}""")
            formatter_js_percent = JsCode("""function(params){if(params.value==null||isNaN(params.value))return'';return params.value.toLocaleString('pl-PL',{style:'percent', minimumFractionDigits:2, maximumFractionDigits:2})}""")
            formatter_js_integer = JsCode("""function(params){if(params.value==null||isNaN(params.value))return'';return Math.round(params.value).toLocaleString('pl-PL')}""")

            # Konfiguracja kolumn (bez zmian)
            gb_acos.configure_column("ID", header_name="ID (SKU)", width=200, filter='agTextColumnFilter', pinned='left')
            gb_acos.configure_column("nazwa", header_name="Nazwa produktu", width=300, filter='agTextColumnFilter')
            gb_acos.configure_column("marka", header_name="Marka", width=150, filter='agTextColumnFilter')
            gb_acos.configure_column("kategoria", header_name="Kategoria", width=150, filter='agTextColumnFilter')
            gb_acos.configure_column("Total Spend", header_name="Spend (Reklama)", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_currency, width=180, sort='desc')
            gb_acos.configure_column("Total Sales", header_name="Sales (Reklama)", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_currency, width=180)
            gb_acos.configure_column("ACOS", header_name="ACOS", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_percent, width=150)
            gb_acos.configure_column("Total Sales (Total)", header_name="Total Sales (Łącznie)", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_currency, width=180)
            gb_acos.configure_column("Total Orders (Total)", header_name="Total Orders (Łącznie)", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_integer, width=180)
            gb_acos.configure_column("TACOS", header_name="TACOS", type=["numericColumn","rightAligned"], valueFormatter=formatter_js_percent, width=150)

            # Logika dynamicznej sumy (bez zmian)
            if 'current_acos_grid_key' not in st.session_state or st.session_state.current_acos_grid_key != grid_key_acos:
                st.session_state.current_acos_grid_key = grid_key_acos
                st.session_state.pinned_acos_row = calculate_acos_summary_row(acos_df)
                st.session_state.acos_grid_state = {} 

            js_function_body = f"""
                if (params.node.rowPinned) {{
                    return {{'fontWeight': 'bold', 'backgroundColor': '#f0f2f6'}};
                }}
                return null;
            """
            cell_style_jscode = JsCode(f"function(params) {{{js_function_body}}}")

            gb_acos.configure_default_column(resizable=True, filterable=True, sortable=True, cellStyle=cell_style_jscode)
            grid_options_acos = gb_acos.build()
            grid_options_acos['pinnedBottomRowData'] = st.session_state.get('pinned_acos_row', None)
            
            # Wyświetlanie siatki (bez zmian)
            grid_response_acos = AgGrid(
                acos_df, 
                gridOptions=grid_options_acos,
                width="100%",
                height=600,
                allow_unsafe_jscode=True,
                theme='ag-theme-alpine',
                key=grid_key_acos,
                update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.FILTERING_CHANGED | GridUpdateMode.SORTING_CHANGED,
                enable_enterprise_modules=True
            )

            # Logika aktualizacji sumy (bez zmian)
            if grid_response_acos['data'] is not None:
                df_filtered_acos = pd.DataFrame(grid_response_acos['data'])
                newly_calculated_acos_row = calculate_acos_summary_row(df_filtered_acos)
                if newly_calculated_acos_row != st.session_state.get('pinned_acos_row', None):
                    st.session_state.pinned_acos_row = newly_calculated_acos_row
                    st.rerun() 

            st.markdown("---")
            # Logika pobierania Excela (bez zmian)
            buffer_acos = io.BytesIO()
            with pd.ExcelWriter(buffer_acos, engine='xlsxwriter') as writer:
                if 'df_filtered_acos' in locals():
                    df_to_export = df_filtered_acos
                else: 
                    df_to_export = acos_df

                df_to_export.to_excel(writer, index=False, sheet_name='ACOS_Data')
                workbook, worksheet = writer.book, writer.sheets['ACOS_Data']

                currency_format = workbook.add_format({'num_format': f'#,##0.00 "{currency_symbol}"'});
                percent_format = workbook.add_format({'num_format': '0.00%'});
                integer_format = workbook.add_format({'num_format': '#,##0'});

                worksheet.set_column('A:A', 25) # ID
                worksheet.set_column('B:B', 40) # nazwa
                worksheet.set_column('C:C', 20) # marka
                worksheet.set_column('D:D', 20) # kategoria
                worksheet.set_column('E:E', 18, currency_format) # Total Spend
                worksheet.set_column('F:F', 18, currency_format) # Total Sales
                worksheet.set_column('G:G', 12, percent_format) # ACOS
                worksheet.set_column('H:H', 18, currency_format) # Total Sales (Total)
                worksheet.set_column('I:I', 18, integer_format) # Total Orders (Total)
                worksheet.set_column('J:J', 12, percent_format) # TACOS

            st.download_button(
                label="📥 Pobierz widoczne dane ACOS (Excel)", 
                data=buffer_acos,
                file_name=f"acos_data_{konto_acos}_{kraj_acos}_{okres_acos}_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
# <--- KONIEC ZAKTUALIZOWANEJ ZAKŁADKI ID ACOS ---

with tab6:
    st.header("Find Product 2 (Wyszukiwarka SKU i Kampanii)")
    st.info("""
    Wyszukaj produkty w centralnej bazie (po ID, SKU, ASIN, Nazwie, Marce, Kategorii). 
    Aplikacja znajdzie wszystkie pasujące produkty, a następnie wyświetli **każdą kampanię reklamową** (ze wszystkich kont i krajów), w której te produkty (SKU) występują.
    """)

    try:
        # 1. Ładujemy obie bazy danych
        with st.spinner("Ładowanie mapy kampanii (ze wszystkich kont)..."):
            campaign_map_df = build_dynamic_product_map()
        
        with st.spinner("Ładowanie centralnej bazy produktów (Marka, Kategoria)..."):
            product_details_df = load_product_details()

        if campaign_map_df.empty or product_details_df.empty:
            st.warning("Nie można załadować danych. Mapa kampanii lub centralna baza produktów są puste.")
        
        else:
            # 2. Pole wyszukiwania
            search_term_tab6 = st.text_input("Wpisz frazy (oddzielone przecinkiem):", key="tab6_search_input_v3") # Zmieniony klucz

            if search_term_tab6:
                search_terms_list = [term.strip().lower() for term in search_term_tab6.split(',') if term.strip()]
                
                if not search_terms_list:
                    st.info("Wpisz frazę, aby rozpocząć wyszukiwanie.")
                
                else:
                    # --- NOWA LOGIKA WYSZUKIWANIA ---

                    # 3. Krok A: Wyszukaj pasujących produktów w centralnej bazie (nazwa, marka, kategoria, SKU, ASIN)
                    search_cols_details = ['SKU', 'ASIN', 'nazwa', 'marka', 'kategoria']
                    mask_details = pd.Series(False, index=product_details_df.index)
                    for term_lower in search_terms_list:
                        for col in search_cols_details:
                            if col in product_details_df.columns:
                                mask_details = mask_details | product_details_df[col].astype(str).str.lower().str.contains(term_lower, na=False)
                    
                    found_in_details = product_details_df[mask_details]
                    
                    # 4. Krok B: Wyszukaj pasujących produktów w mapie kampanii (tylko po SKU i ASIN)
                    search_cols_campaign_map = ['SKU', 'ASIN']
                    mask_campaign = pd.Series(False, index=campaign_map_df.index)
                    for term_lower in search_terms_list:
                         for col in search_cols_campaign_map:
                            if col in campaign_map_df.columns:
                                mask_campaign = mask_campaign | campaign_map_df[col].astype(str).str.lower().str.contains(term_lower, na=False)
                    
                    found_in_campaign_map = campaign_map_df[mask_campaign]

                    # 5. Krok C: Zbierz unikalną listę wszystkich pasujących SKU z obu wyszukiwań
                    sku_list_from_details = set(found_in_details['SKU'].unique())
                    sku_list_from_campaign_map = set(found_in_campaign_map['SKU'].unique())
                    
                    final_sku_list = list(sku_list_from_details.union(sku_list_from_campaign_map))
                    
                    if not final_sku_list:
                        st.warning(f"Nie znaleziono żadnych SKU pasujących do: '{', '.join(search_terms_list)}'")
                    else:
                        # 6. Krok D: Użyj listy SKU, aby wyfiltrować *wszystkie* powiązane kampanie
                        results_df_tab6 = campaign_map_df[campaign_map_df['SKU'].isin(final_sku_list)].copy()

                        # 7. Krok E: Połącz znalezione kampanie z danymi z centralnej bazy, aby je wzbogacić
                        details_to_merge = product_details_df[['SKU', 'nazwa', 'marka', 'kategoria']].drop_duplicates(subset=['SKU'])
                        
                        final_display_df = pd.merge(
                            results_df_tab6,
                            details_to_merge,
                            on='SKU',
                            how='left'
                        )
                        
                        # Wypełnij braki, jeśli SKU z kampanii nie było w centralnej bazie
                        final_display_df[['nazwa', 'marka', 'kategoria']] = final_display_df[['nazwa', 'marka', 'kategoria']].fillna('')

                        st.markdown(f"**Znaleziono {len(final_display_df)} powiązanych wierszy kampanii dla pasujących SKU.**")

                        # 8. Definiujemy i filtrujemy ostateczne kolumny do wyświetlenia
                        display_cols_order = [
                            'SKU', 'nazwa', 'marka', 'kategoria', 
                            'Account', 'Country', 'Campaign', 'ASIN',
                            'Campaign Type', 'Targeting Type', 'Price', 'Quantity'
                        ]
                        
                        existing_display_cols = [col for col in display_cols_order if col in final_display_df.columns]
                        final_display_df = final_display_df[existing_display_cols].drop_duplicates()

                        # 9. Wyświetlanie AgGrid
                        gb_tab6 = GridOptionsBuilder.from_dataframe(final_display_df)
                        gb_tab6.configure_default_column(resizable=True, filterable=True, sortable=True, autoHeaderHeight=True, wrapText=True)
                        
                        # Konfiguracja kolumn
                        if 'SKU' in final_display_df.columns: gb_tab6.configure_column("SKU", pinned='left', width=150)
                        if 'nazwa' in final_display_df.columns: gb_tab6.configure_column("nazwa", header_name="Nazwa Produktu", pinned='left', width=300)
                        if 'marka' in final_display_df.columns: gb_tab6.configure_column("marka", header_name="Marka", width=150)
                        if 'kategoria' in final_display_df.columns: gb_tab6.configure_column("kategoria", header_name="Kategoria", width=150)
                        if 'Account' in final_display_df.columns: gb_tab6.configure_column("Account", width=120)
                        if 'Country' in final_display_df.columns: gb_tab6.configure_column("Country", width=120)
                        if 'Campaign' in final_display_df.columns: gb_tab6.configure_column("Campaign", width=350)
                        if 'ASIN' in final_display_df.columns: gb_tab6.configure_column("ASIN", width=150)
                        if 'Price' in final_display_df.columns: gb_tab6.configure_column("Price", header_name="Cena", type=["numericColumn","rightAligned"], width=100)
                        if 'Quantity' in final_display_df.columns: gb_tab6.configure_column("Quantity", header_name="Ilość", type=["numericColumn","rightAligned"], width=100)

                        grid_options_tab6 = gb_tab6.build()
                        
                        AgGrid(
                            final_display_df, 
                            gridOptions=grid_options_tab6, 
                            height=600, 
                            width='100%', 
                            allow_unsafe_jscode=True, 
                            theme='ag-theme-alpine', 
                            key='find_product_2_grid_v3', # Zmieniony klucz
                            enable_enterprise_modules=True
                        )
            else:
                st.info("Wpisz frazę (np. nazwę, SKU, kategorię), aby znaleźć produkt i powiązane z nim kampanie.")

    except Exception as e:
        st.error(f"Wystąpił krytyczny błąd w zakładce 'Find Product 2': {e}")
        st.exception(e) # Dodaje pełny traceback błędu
