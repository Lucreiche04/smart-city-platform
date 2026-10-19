# Backlog V2 — évolutions possibles

| Priorité | Évolution | Valeur pour le client |
|---|---|---|
| Haute | Vraies données de mobilité (API Île-de-France Mobilités, comptages routiers data.gouv.fr) en entrée du modèle | Meilleure prévision et mesure de l'effet des restrictions de circulation |
| Haute | Prévision par zone (un modèle par capteur) et à J+2 / J+3 | Anticiper davantage les mesures préventives |
| Haute | XGBoost / LightGBM avec optimisation des hyperparamètres quand l'historique dépasse 1 an | Gain de précision |
| Moyenne | Notifications push mobiles (PWA) en plus des emails | Toucher davantage de citoyens |
| Moyenne | MQTT sécurisé : authentification par capteur + TLS (port 8883) | Indispensable avec de vrais capteurs |
| Moyenne | Comparaison avant/après d'une mesure de restriction de circulation | Argumentaire chiffré pour les élus |
| Moyenne | Rôles distincts (admin, analyste, élu) | Moindre privilège |
| Basse | Multi-villes | Mutualisation entre métropoles |
| Basse | Open data : publication des mesures des capteurs | Transparence |
