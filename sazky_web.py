import streamlit as st
import sqlite3
import os
import pandas as pd

# Konstanty
ABSTRAKTNI_BODY = {
    "1.G": 0, "2.G": 0, "3.G": 0, "4.G": 0,
    "5.G": 0, "1.A": 0, "1.B": 0, "1.C": 0,
    "6.G": 0, "2.A": 0, "2.B": 0, "2.C": 0,
    "3.A": 0, "3.B": 0, "3.C": 0
}

ROCNIKY = {
    "Kategorie I.": ["1.G", "2.G", "3.G", "4.G"],
    "Kategorie II.": ["5.G", "1.A", "1.B", "1.C"],
    "Kategorie III.": ["6.G", "2.A", "2.B", "2.C"],
    "Kategorie IV.": ["3.A", "3.B", "3.C"]
}

DB_FILE = "/tmp/nsd_points_web.db"

# Databázové funkce
def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS points (
            class_name TEXT PRIMARY KEY,
            points INTEGER
        )
    ''')
    for tridy in ROCNIKY.values():
        for class_name in tridy:
            cursor.execute('''
                INSERT OR IGNORE INTO points (class_name, points)
                VALUES (?, ?)
            ''', (class_name, 0))
    conn.commit()
    conn.close()

def get_all_points():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT class_name, points FROM points')
    points = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return points

def update_points(points_dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    for class_name, points in points_dict.items():
        cursor.execute('''
            UPDATE points
            SET points = ?
            WHERE class_name = ?
        ''', (points, class_name))
    conn.commit()
    conn.close()

# Inicializace databáze
if not os.path.exists(DB_FILE):
    init_database()

st.set_page_config(page_title="Sázky NSD", layout="wide")
st.title("Sázky - NSD (webová verze)")

st.write("Aplikace se načetla!")

# Načtení bodů
data = get_all_points()

# --- ADMIN SEKCE ---
with st.expander("🔑 Admin sekce (úprava bodů)"):
    admin_pass = st.text_input("Zadej heslo pro admina:", type="password")
    if admin_pass == "G26":
        st.success("Přístup povolen!")
        new_points = {}
        for rocnik, tridy in ROCNIKY.items():
            st.markdown(f"**{rocnik}**")
            cols = st.columns(len(tridy))
            for i, class_name in enumerate(tridy):
                val = cols[i].number_input(f"{class_name}", min_value=-999, max_value=999, value=data[class_name], key=f"admin_{class_name}")
                new_points[class_name] = val
        if st.button("Uložit změny", key="save_admin"):
            update_points(new_points)
            st.success("Body byly uloženy!")
            st.experimental_rerun()
    elif admin_pass:
        st.error("Nesprávné heslo!")

# --- SÁZKY ---
st.header("Sázení tříd")
bets = {}
for rocnik, tridy in ROCNIKY.items():
    st.subheader(rocnik)
    for class_name in tridy:
        col1, col2 = st.columns([2,2])
        bet_on = col1.selectbox(f"{class_name} sází na:", tridy, key=f"beton_{class_name}")
        bet_amount = col2.number_input(f"Kolik bodů sází {class_name}?", min_value=0, max_value=5, value=0, key=f"betamt_{class_name}")
        bets[class_name] = {"target": bet_on, "amount": bet_amount}

# --- VYHLÁŠENÍ VÍTĚZE ---
st.header("Vyhlášení vítěze a výpočet bodů")
winners = {}
for rocnik, tridy in ROCNIKY.items():
    winners[rocnik] = st.selectbox(f"Vítěz pro {rocnik}", tridy, key=f"winner_{rocnik}")

if st.button("Vyhlásit vítěze a spočítat body", key="calc_results"):
    new_points = data.copy()
    vysledky = {}
    for rocnik, tridy in ROCNIKY.items():
        winner = winners[rocnik]
        for class_name in tridy:
            bet = bets[class_name]
            if bet["amount"] > 0:
                if bet["target"] == winner:
                    new_points[class_name] += bet["amount"]
                    vysledek = f"Vyhráli {bet['amount']} bodů"
                else:
                    new_points[class_name] -= bet["amount"]
                    vysledek = f"Prohráli {bet['amount']} bodů"
            else:
                vysledek = "Bez sázky"
            vysledky[class_name] = vysledek
    update_points(new_points)
    st.success("Body byly aktualizovány!")
    st.write("### Výsledky:")
    for rocnik, tridy in ROCNIKY.items():
        st.markdown(f"**{rocnik}**")
        for class_name in tridy:
            st.write(f"{class_name}: {new_points[class_name]} bodů ({vysledky[class_name]})")
    st.experimental_rerun()

# --- TABULKA BODŮ ---
st.header("Přehled tříd a aktuálních bodů")
tab = []
for rocnik, tridy in ROCNIKY.items():
    for class_name in tridy:
        pl = data[class_name] - ABSTRAKTNI_BODY[class_name]
        tab.append({
            "Třída": class_name,
            "Body": data[class_name],
            "P/L": pl
        })
df = pd.DataFrame(tab)
def color_pl(val):
    if val > 0:
        return 'color: #00cc44; font-weight: bold;'
    elif val < 0:
        return 'color: #ff3333; font-weight: bold;'
    else:
        return ''
st.dataframe(df.style.applymap(color_pl, subset=["P/L"])) 