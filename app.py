"""Application Streamlit : Comparateur de VAN de deux projets."""
from typing import List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Comparateur VAN - 2 Projets", page_icon="📊", layout="wide")

# ---------- Fonctions financières ----------

def calcul_van(investissement: float, flux: List[float], taux: float) -> float:
    """VAN = -I0 + somme(CFt / (1+r)^t)."""
    van = -investissement
    for t, cf in enumerate(flux, start=1):
        van += cf / ((1 + taux) ** t)
    return van


def flux_actualises(flux: List[float], taux: float) -> List[float]:
    return [cf / ((1 + taux) ** t) for t, cf in enumerate(flux, start=1)]


def van_cumulee(investissement: float, flux: List[float], taux: float) -> List[float]:
    """Retourne la VAN cumulee annee par annee (inclut t0 = -I0)."""
    fa = flux_actualises(flux, taux)
    cumul = [-investissement]
    total = -investissement
    for v in fa:
        total += v
        cumul.append(total)
    return cumul


def calcul_tri(investissement: float, flux: List[float]) -> Optional[float]:
    """TRI par dichotomie : taux r tel que VAN(r) = 0. Retourne None si introuvable."""
    def van_r(r):
        if r <= -1:
            return float("inf")
        return calcul_van(investissement, flux, r)

    bas, haut = -0.9, 5.0
    van_bas, van_haut = van_r(bas), van_r(haut)
    if van_bas * van_haut > 0:
        return None
    for _ in range(200):
        mid = (bas + haut) / 2
        van_mid = van_r(mid)
        if abs(van_mid) < 1e-6:
            return mid
        if van_bas * van_mid <= 0:
            haut, van_haut = mid, van_mid
        else:
            bas, van_bas = mid, van_mid
    return (bas + haut) / 2


def calcul_drci(investissement: float, flux: List[float], taux: float) -> Optional[int]:
    """Delai de recuperation actualise (en annees). None si jamais recupere."""
    cumul = van_cumulee(investissement, flux, taux)
    for annee in range(1, len(cumul)):
        if cumul[annee] >= 0:
            return annee
    return None


def saisie_projet(nom_defaut: str, key_prefix: str, duree: int):
    """Bloc de saisie pour un projet."""
    st.subheader(nom_defaut)
    nom = st.text_input("Nom du projet", value=nom_defaut, key=f"{key_prefix}_nom")
    i0 = st.number_input(
        "Investissement initial (EUR)", min_value=0.0,
        value=10000.0 if key_prefix == "A" else 15000.0,
        step=1000.0, key=f"{key_prefix}_i0"
    )
    mode = st.selectbox(
        "Mode de saisie des flux",
        ["Manuelle annee par annee", "Flux constant + croissance"],
        key=f"{key_prefix}_mode"
    )
    if mode == "Flux constant + croissance":
        base = st.number_input("Flux annee 1 (EUR)", value=3000.0, step=500.0, key=f"{key_prefix}_base")
        croissance = st.number_input("Croissance annuelle (%)", value=5.0, step=1.0, key=f"{key_prefix}_croiss") / 100
        flux = [base * ((1 + croissance) ** t) for t in range(duree)]
        st.info("Flux generes : " + ", ".join(f"{x:,.0f} EUR".replace(",", " ") for x in flux))
    else:
        flux = []
        cols = st.columns(min(duree, 3))
        for i in range(duree):
            with cols[i % len(cols)]:
                val_defaut = 3000.0 if key_prefix == "A" else 4000.0
                v = st.number_input(
                    f"Flux annee {i+1} (EUR)", value=float(val_defaut),
                    step=500.0, key=f"{key_prefix}_cf{i}"
                )
                flux.append(v)
    return {"nom": nom, "i0": i0, "flux": flux}


# ---------- Interface ----------

st.title("Comparateur de VAN de deux projets")
st.markdown(
    "Comparez la **Valeur Actuelle Nette (VAN)** de deux projets d'investissement "
    "avec illustration graphique : flux, VAN cumulee et sensibilite au taux."
)

with st.sidebar:
    st.header("Parametres generaux")
    duree = st.slider("Duree d'analyse (annees)", 1, 15, 5)
    taux_commun = st.number_input("Taux d'actualisation commun (%)", value=8.0, min_value=0.0, max_value=50.0, step=0.5) / 100
    taux_differencies = st.checkbox("Taux differencies par projet", value=False)
    if taux_differencies:
        taux_a_input = st.number_input("Taux Projet A (%)", value=8.0, min_value=0.0, max_value=50.0, step=0.5) / 100
        taux_b_input = st.number_input("Taux Projet B (%)", value=10.0, min_value=0.0, max_value=50.0, step=0.5) / 100
    else:
        taux_a_input = taux_b_input = taux_commun

st.markdown("---")

colA, colB = st.columns(2)
with colA:
    proj_a = saisie_projet("Projet A", "A", duree)
with colB:
    proj_b = saisie_projet("Projet B", "B", duree)

# ---------- Calculs ----------
taux_a, taux_b = taux_a_input, taux_b_input

van_a = calcul_van(proj_a["i0"], proj_a["flux"], taux_a)
van_b = calcul_van(proj_b["i0"], proj_b["flux"], taux_b)

tri_a = calcul_tri(proj_a["i0"], proj_a["flux"])
tri_b = calcul_tri(proj_b["i0"], proj_b["flux"])

ip_a = (van_a + proj_a["i0"]) / proj_a["i0"] if proj_a["i0"] > 0 else 0
ip_b = (van_b + proj_b["i0"]) / proj_b["i0"] if proj_b["i0"] > 0 else 0

drci_a = calcul_drci(proj_a["i0"], proj_a["flux"], taux_a)
drci_b = calcul_drci(proj_b["i0"], proj_b["flux"], taux_b)

# ---------- KPIs ----------
st.markdown("---")
st.header("Resultats compares")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric(f"VAN {proj_a['nom']}", f"{van_a:,.0f} EUR".replace(",", " "), delta=f"TRI {tri_a*100:.1f} %" if tri_a else "TRI n/a")
with k2:
    st.metric(f"VAN {proj_b['nom']}", f"{van_b:,.0f} EUR".replace(",", " "), delta=f"TRI {tri_b*100:.1f} %" if tri_b else "TRI n/a")
with k3:
    st.metric("Ecart de VAN (A - B)", f"{van_a - van_b:,.0f} EUR".replace(",", " "))
with k4:
    gagnant = proj_a["nom"] if van_a > van_b else proj_b["nom"] if van_b > van_a else "Egalite"
    st.metric("Projet le plus rentable", gagnant)

if van_a > 0 and van_b > 0:
    st.success(f"Les deux projets sont rentables (VAN > 0). Le meilleur choix est **{gagnant}**.")
elif van_a > 0 or van_b > 0:
    meilleur = proj_a["nom"] if van_a > 0 else proj_b["nom"]
    st.warning(f"Un seul projet est rentable : **{meilleur}**. L'autre a une VAN negative.")
else:
    st.error("Aucun projet n'est rentable (VAN < 0 pour les deux).")

recap = pd.DataFrame({
    "Indicateur": ["Investissement initial (EUR)", "VAN (EUR)", "TRI (%)", "Indice de profitabilite", "DRCI (annees)"],
    proj_a["nom"]: [
        f"{proj_a['i0']:,.0f}".replace(",", " "),
        f"{van_a:,.0f}".replace(",", " "),
        f"{tri_a*100:.2f}" if tri_a else "n/a",
        f"{ip_a:.2f}",
        str(drci_a) if drci_a else "Jamais",
    ],
    proj_b["nom"]: [
        f"{proj_b['i0']:,.0f}".replace(",", " "),
        f"{van_b:,.0f}".replace(",", " "),
        f"{tri_b*100:.2f}" if tri_b else "n/a",
        f"{ip_b:.2f}",
        str(drci_b) if drci_b else "Jamais",
    ],
})
st.table(recap)

# ---------- Graphiques ----------
st.markdown("---")
st.header("Illustrations graphiques")

annees = list(range(1, duree + 1))

st.subheader("1. Flux de tresorerie annuels (non actualises)")
fig1, ax1 = plt.subplots(figsize=(8, 4))
x = np.arange(duree)
largeur = 0.35
ax1.bar(x - largeur/2, proj_a["flux"], largeur, label=proj_a["nom"])
ax1.bar(x + largeur/2, proj_b["flux"], largeur, label=proj_b["nom"])
ax1.set_xticks(x)
ax1.set_xticklabels([f"Annee {a}" for a in annees], rotation=30)
ax1.set_ylabel("Flux (EUR)")
ax1.set_title("Flux de tresorerie compares")
ax1.legend()
ax1.grid(axis="y", alpha=0.3)
fig1.tight_layout()
st.pyplot(fig1)
plt.close(fig1)

st.subheader("2. VAN cumulee (flux actualises)")
cumul_a = van_cumulee(proj_a["i0"], proj_a["flux"], taux_a)
cumul_b = van_cumulee(proj_b["i0"], proj_b["flux"], taux_b)
fig2, ax2 = plt.subplots(figsize=(8, 4))
ax2.plot(range(duree + 1), cumul_a, marker="o", label=f"{proj_a['nom']} (taux {taux_a*100:.1f}%)")
ax2.plot(range(duree + 1), cumul_b, marker="s", label=f"{proj_b['nom']} (taux {taux_b*100:.1f}%)")
ax2.axhline(0, color="red", linestyle="--", linewidth=1)
ax2.set_xticks(range(duree + 1))
ax2.set_xticklabels(["T0"] + [f"A{a}" for a in annees])
ax2.set_ylabel("VAN cumulee (EUR)")
ax2.set_title("Trajectoire de creation de valeur")
ax2.legend()
ax2.grid(alpha=0.3)
fig2.tight_layout()
st.pyplot(fig2)
plt.close(fig2)
st.caption("La courbe qui franchit 0 le plus tot a le meilleur delai de recuperation. La valeur finale = VAN du projet.")

st.subheader("3. Sensibilite de la VAN au taux d'actualisation")
taux_range = np.linspace(0, 0.30, 61)
vans_a = [calcul_van(proj_a["i0"], proj_a["flux"], r) for r in taux_range]
vans_b = [calcul_van(proj_b["i0"], proj_b["flux"], r) for r in taux_range]
fig3, ax3 = plt.subplots(figsize=(8, 4))
ax3.plot(taux_range * 100, vans_a, label=proj_a["nom"])
ax3.plot(taux_range * 100, vans_b, label=proj_b["nom"])
ax3.axhline(0, color="red", linestyle="--", linewidth=1)
ax3.scatter([taux_a*100], [van_a], s=80, zorder=5)
ax3.scatter([taux_b*100], [van_b], s=80, zorder=5)
ax3.set_xlabel("Taux d'actualisation (%)")
ax3.set_ylabel("VAN (EUR)")
ax3.set_title("VAN = f(taux) - le TRI est l'intersection avec 0")
ax3.legend()
ax3.grid(alpha=0.3)
fig3.tight_layout()
st.pyplot(fig3)
plt.close(fig3)

# ---------- Detail ----------
st.markdown("---")
st.header("Detail annee par annee")
fa_a = flux_actualises(proj_a["flux"], taux_a)
fa_b = flux_actualises(proj_b["flux"], taux_b)
detail = pd.DataFrame({
    "Annee": annees,
    f"Flux {proj_a['nom']}": proj_a["flux"],
    f"Flux actualise {proj_a['nom']}": np.round(fa_a, 2),
    f"Flux {proj_b['nom']}": proj_b["flux"],
    f"Flux actualise {proj_b['nom']}": np.round(fa_b, 2),
})
st.dataframe(detail, use_container_width=True)
csv = detail.to_csv(index=False).encode("utf-8")
st.download_button("Telecharger le detail (CSV)", csv, "detail_van.csv", "text/csv")

st.markdown("---")
st.markdown("Formule VAN : VAN = -I0 + somme CFt / (1+r)^t | TRI : taux r tel que VAN(r)=0 | IP : (VAN+I0)/I0")
