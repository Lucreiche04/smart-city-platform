# Registre des traitements de données (RGPD, article 30)

| Champ | Traitement 1 : alertes email citoyennes | Traitement 2 : comptes administrateurs | Traitement 3 : journal de sécurité |
|---|---|---|---|
| Responsable | Direction de la Transition Écologique de la Métropole | idem | idem |
| Finalité | Prévenir les abonnés d'un épisode de pollution | Accès à l'espace d'administration | Traçabilité des accès et actions sensibles |
| Base légale | Consentement (case à cocher non pré-cochée) | Exécution d'une mission d'intérêt public | Intérêt légitime (sécurité du système) |
| Données | Adresse email, date d'abonnement | Identifiant, mot de passe haché (bcrypt) | Identifiant, action, adresse IP, horodatage |
| Personnes concernées | Citoyens abonnés | Agents de la métropole | Agents, visiteurs de l'API d'abonnement |
| Destinataires | Aucun tiers (envoi via le serveur SMTP de la métropole) | Aucun | Administrateurs |
| Durée de conservation | Jusqu'à désabonnement | Durée de la mission de l'agent | 12 mois |
| Droits | Suppression immédiate via la page Confidentialité (`DELETE /api/subscribers/{email}`) | Sur demande | Sur demande |
| Sécurité | HTTPS, base non exposée sur Internet | bcrypt + JWT expirant en 60 min, limitation 5 tentatives/min | Base non exposée |

## Données NON personnelles
- Mesures de pollution et météo : données environnementales, aucune personne identifiable.
- Capteurs IoT : position arrondie au centre du quartier (pas de géolocalisation précise).
- Pas de cookies d'audience : aucun bandeau cookies nécessaire. Si une analytics est ajoutée en V2, prévoir un bandeau de consentement (exigence du client).
