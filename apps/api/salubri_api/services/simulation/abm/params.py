# SPDX-License-Identifier: AGPL-3.0-or-later
"""Paramètres propres au modèle à agents (docs/SIMULATION_ODD.md § 7). [H] = hypothèse de travail."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AbmParams:
    heterogeneite: bool = True  # False : ménages identiques, règles réduites au modèle agrégé (ODD § 8)
    # ménages
    revenu_parts: tuple[float, float, float] = (0.50, 0.35, 0.15)  # [H] faible / moyen / élevé
    revenu_fcfa_mois: tuple[float, float, float] = (40_000.0, 90_000.0, 250_000.0)  # [H]
    sigma_production: float = 0.3  # [H] dispersion log-normale de la production par ménage
    jitter_distance_m: float = 50.0  # [H] position du ménage dans l'îlot
    alpha_porter: float = 8.0  # porter quand c'est possible : P > 0,999 sans les autres termes
    beta_dist_porter: float = 0.3  # [H] par 100 m de marche
    beta_reg: float = 2.0  # [H] régularité vécue sur 7 jours → attendre le pré-collecteur
    beta_norme: float = 2.0  # [H] part de l'îlot qui a jeté sur 7 jours
    norme_reference: float = 0.2
    beta_habitude: float = 0.5  # [H] refaire le choix de la veille
    # abonnement mensuel (calés pour retrouver sub_up / sub_down du modèle agrégé au point de référence)
    a_abo: float = -3.11
    a_desabo: float = -4.93
    beta_reg_mois: float = 4.0  # [H]
    beta_prix: float = 20.0  # [H] par unité de (prix / revenu mensuel)
    # pré-collecteurs
    extension_marge: float = 1.5  # [H] revenu ≥ 1,5 × coût …
    extension_charge_max: float = 0.7  # [H] … et charrette remplie à moins de 70 % → reprend des îlots
    # brigade Laabal
    amende_fcfa: float = 5000.0  # [H]
    # mairie
    priorite_recurrent: float = 1.3
