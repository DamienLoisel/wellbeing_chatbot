"""
Services pour l'analyse des messages et la détection de la détresse psychologique
"""
from typing import Dict, List
from openai import OpenAI
import os
from dotenv import load_dotenv
from .models import Employee, ViolentWord, PsychologicalTheme, EmployeeThemeCounter
from django.db.models import F
import re
import logging

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Liste des signaux de détresse à détecter
DISTRESS_SIGNALS = [
    "stress", "anxiété", "dépression", "burnout", "épuisement",
    "isolement", "surcharge", "pression", "conflit", "harcèlement"
]

# Liste de mots-clés liés au milieu professionnel
WORKPLACE_KEYWORDS = [
    "travail", "entreprise", "bureau", "collègue", "patron", "manager", "employé",
    "réunion", "projet", "client", "racisme", "harcèlement", "discrimination",
    "stress", "burnout", "pression", "conflit", "professionnel", "boulot", "job",
    "équipe", "hiérarchie", "supérieur", "collaborateur", "carrière", "promotion",
    "licenciement", "démission", "contrat", "salaire", "rémunération", "congé",
    "formation", "compétence", "performance", "objectif", "évaluation", "feedback",
    "communication", "relation", "tension", "ambiance", "culture", "valeur", "éthique"
]

# Liste des sujets sensibles qui doivent toujours être traités comme professionnels
SENSITIVE_WORKPLACE_TOPICS = [
    "racisme", "raciste", "discrimination raciale",
    "harcèlement", "harcelé", "harceler",
    "discrimination", "discriminé", "discriminer",
    "sexisme", "sexiste", "agression", "violence", "menace",
    "intimidation", "intimidé", "intimider",
    "mobbing", "burn-out", "burnout", "surmenage",
    "pression", "stress", "anxiété", "dépression"
]

SYSTEM_PROMPT = """Vous êtes un assistant spécialisé UNIQUEMENT dans le soutien psychologique en entreprise.

VOTRE RÔLE EST STRICTEMENT LIMITÉ À :
- Écouter et détecter les signaux de détresse psychologique au travail
- Fournir un soutien émotionnel pour les situations professionnelles uniquement
- Rester professionnel et empathique dans le contexte de l'entreprise
- Encourager une communication positive au travail

LIMITES STRICTES (ne jamais les dépasser) :
- NE PAS poser de diagnostic médical
- NE PAS prescrire de traitement ou de médicament
- NE PAS donner de conseil juridique
- NE PAS traiter de sujets personnels ou hors contexte professionnel
- NE PAS suggérer de solutions pour des problèmes non liés au travail

IMPORTANT : Considérez par défaut que les messages de l'utilisateur sont dans un contexte professionnel, sauf s'ils mentionnent explicitement un contexte personnel ou familial sans lien avec le travail.

SUJETS SPÉCIFIQUES À TRAITER COMME PROFESSIONNELS :
- Le racisme au travail est TOUJOURS considéré comme un sujet professionnel
- Le harcèlement est TOUJOURS considéré comme un sujet professionnel
- La discrimination est TOUJOURS considérée comme un sujet professionnel
- Tous les sujets liés au stress, à l'anxiété ou à la pression au travail sont TOUJOURS considérés comme professionnels
- Les conflits interpersonnels en milieu de travail sont TOUJOURS considérés comme professionnels

GESTION DES INTERACTIONS :
1. Pour les questions/situations liées au travail :
   - Répondre de manière professionnelle et empathique
   - Fournir un soutien adapté au contexte professionnel
   - Valoriser les efforts et progrès professionnels

2. Pour les expressions de reconnaissance ou d'amabilité professionnelle :
   - Accueillir positivement ces marques de reconnaissance
   - Répondre avec chaleur tout en restant professionnel
   - Encourager cette attitude positive au travail
   Exemples :
   - "Je vous remercie de votre confiance. C'est important de maintenir un dialogue constructif au travail."
   - "Votre attitude positive est précieuse dans l'environnement professionnel. Avez-vous besoin d'aide pour autre chose ?"

3. Pour les formules de politesse simples :
   - Répondre brièvement et poliment
   - Maintenir un ton professionnel
   Exemples : "Je vous en prie.", "Bonjour, comment puis-je vous aider ?", "Au revoir, n'hésitez pas à revenir si besoin."

4. Pour tout sujet hors contexte professionnel :
   "Je suis désolé, mais je suis uniquement conçu pour aider avec les situations de stress et de bien-être psychologique dans le contexte professionnel."

STYLE DE RÉPONSE :
- Ton : professionnel, empathique et constructif
- Langage : clair et bienveillant
- Focus : uniquement sur les situations professionnelles
- Approche : valorisante et orientée solutions professionnelles"""

ANALYSIS_PROMPT = """
En plus de votre réponse principale, analysez le message de l'utilisateur et identifiez tous les mots ou expressions qui pourraient indiquer de la violence, de la détresse psychologique, de l'anxiété, du stress, ou d'autres problèmes de santé mentale dans un contexte professionnel.

IMPORTANT : Considérez par défaut que les messages de l'utilisateur sont dans un contexte professionnel, même s'ils ne le mentionnent pas explicitement. Un message doit être considéré hors sujet uniquement s'il traite clairement de sujets personnels sans lien avec le travail (comme la santé familiale, les loisirs personnels, etc.).

SUJETS SPÉCIFIQUES À TRAITER COMME PROFESSIONNELS :
- Tout message mentionnant le racisme doit TOUJOURS être considéré comme un sujet professionnel (scopeflag = false)
- Tout message mentionnant le harcèlement doit TOUJOURS être considéré comme un sujet professionnel (scopeflag = false)
- Tout message mentionnant la discrimination doit TOUJOURS être considéré comme un sujet professionnel (scopeflag = false)
- Tout message mentionnant le stress, l'anxiété ou la pression doit TOUJOURS être considéré comme un sujet professionnel (scopeflag = false)
- Tout message mentionnant des conflits interpersonnels doit TOUJOURS être considéré comme un sujet professionnel (scopeflag = false)

Votre réponse doit être structurée en JSON avec trois parties :
1. "response": votre réponse normale au message de l'utilisateur
2. "violent_words": un tableau des mots ou expressions identifiés comme violents ou indiquant de la détresse
3. "scopeflag": un booléen qui indique si le message est hors sujet (true = hors sujet, false = dans le sujet professionnel)

Exemple de format:
{
  "response": "Votre réponse normale ici...",
  "violent_words": ["mot1", "expression2", "mot3"],
  "scopeflag": false
}

Si le message est hors du contexte professionnel (par exemple, une question médicale personnelle ou un sujet sans rapport avec le travail), mettez "scopeflag" à true.
Si aucun mot violent ou indiquant de la détresse n'est détecté, "violent_words" doit être un tableau vide.
"""

def preprocess_text(text: str) -> List[str]:
    """
    Prétraite le texte pour l'analyse

    Args:
        text (str): Texte à prétraiter

    Returns:
        List[str]: Liste des mots du texte
    """
    # Convertir en minuscules
    text = text.lower()

    # Supprimer la ponctuation et diviser en mots
    words = re.findall(r'\b\w+\b', text)

    return words

def contains_sensitive_topic(message: str) -> Dict:
    """
    Vérifie si le message contient des sujets sensibles liés au milieu professionnel

    Args:
        message (str): Le message à analyser

    Returns:
        Dict: Dictionnaire contenant les résultats de l'analyse
    """
    message_lower = message.lower()

    # Vérifier pour chaque catégorie de sujets sensibles
    results = {
        "contains_racism": any(term in message_lower for term in ["racisme", "raciste", "discrimination raciale"]),
        "contains_harassment": any(term in message_lower for term in ["harcèlement", "harcelé", "harceler"]),
        "contains_discrimination": any(term in message_lower for term in ["discrimination", "discriminé", "discriminer"]),
        "contains_stress": any(term in message_lower for term in ["stress", "anxiété", "pression", "burnout", "épuisement"]),
        "contains_conflict": any(term in message_lower for term in ["conflit", "tension", "dispute", "désaccord"])
    }

    # Vérifier pour tous les mots-clés sensibles
    results["contains_any_sensitive"] = any(term in message_lower for term in SENSITIVE_WORKPLACE_TOPICS)

    # Vérifier pour tous les mots-clés du milieu professionnel
    results["contains_workplace_context"] = any(keyword in message_lower for keyword in WORKPLACE_KEYWORDS)

    # Si le message contient des mots sensibles, le considérer automatiquement comme professionnel
    results["force_professional_context"] = results["contains_any_sensitive"]

    return results

def get_appropriate_response_for_topic(topic_type: str) -> str:
    """
    Génère une réponse appropriée pour un sujet sensible spécifique

    Args:
        topic_type (str): Le type de sujet sensible (racism, harassment, etc.)

    Returns:
        str: Une réponse appropriée pour ce sujet
    """
    responses = {
        "racism": "Je suis désolé d'apprendre que vous avez vécu une situation de racisme. Il est important de signaler ce type de comportement inacceptable en entreprise. Avez-vous besoin de soutien ou d'assistance pour faire face à cette situation au travail ?",

        "harassment": "Je suis désolé d'apprendre que vous faites face à une situation de harcèlement. Ce type de comportement est inacceptable en milieu professionnel. Avez-vous pu en parler à votre service RH ou à une personne de confiance dans votre entreprise ?",

        "discrimination": "Je comprends que vous faites face à une situation de discrimination, ce qui est très préoccupant. Ce type de comportement est illégal en milieu de travail. Avez-vous envisagé de documenter ces incidents et d'en informer les ressources humaines ?",

        "stress": "Je comprends que vous ressentez du stress dans votre environnement professionnel. C'est une préoccupation légitime qui mérite attention. Pouvez-vous me parler davantage de ce qui contribue à ce stress au travail ?",

        "conflict": "Je comprends que vous êtes confronté à un conflit en milieu professionnel. Ces situations peuvent être difficiles à gérer. Pouvez-vous me donner plus de détails sur la nature de ce conflit afin que je puisse vous offrir un meilleur soutien ?"
    }

    return responses.get(topic_type, "Je comprends que vous faites face à une situation difficile dans votre environnement professionnel. Pouvez-vous me donner plus de détails pour que je puisse vous offrir un soutien adapté ?")

def analyze_message(message: str, employee_id: int = None) -> Dict:
    """
    Analyse le message pour détecter les signaux de détresse et générer une réponse appropriée

    Args:
        message (str): Le message de l'utilisateur à analyser
        employee_id (int, optional): ID de l'employé qui envoie le message

    Returns:
        Dict: Dictionnaire contenant la réponse générée, les signaux détectés et l'analyse des mots
    """
    # Analyser le message pour détecter les sujets sensibles
    topic_analysis = contains_sensitive_topic(message)

    # Journaliser pour le débogage
    logger.info(f"Message: {message}")
    logger.info(f"Topic analysis: {topic_analysis}")

    # Analyse OpenAI pour la réponse et l'analyse des mots violents en un seul appel
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + ANALYSIS_PROMPT},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Extraire la réponse JSON
        content = response.choices[0].message.content
        import json
        parsed_response = json.loads(content)

        response_text = parsed_response.get("response", "Je n'ai pas pu analyser votre message correctement.")
        violent_words = parsed_response.get("violent_words", [])
        scopeflag = parsed_response.get("scopeflag", False)

        # Surcharger le scopeflag si des mots-clés liés au travail sont détectés
        # ou si le message concerne spécifiquement un sujet sensible
        if topic_analysis["contains_workplace_context"] or topic_analysis["force_professional_context"]:
            scopeflag = False
            logger.info("Overriding scopeflag to false due to workplace context or sensitive topic")

        # Si le message contient un sujet sensible mais a été marqué comme hors sujet,
        # corriger la réponse avec une réponse appropriée
        if topic_analysis["force_professional_context"] and (scopeflag or "uniquement conçu pour aider" in response_text):
            logger.info("Message contains sensitive topic but was marked out of scope - correcting")
            scopeflag = False

            # Déterminer le type de sujet sensible pour générer une réponse appropriée
            if topic_analysis["contains_racism"]:
                response_text = get_appropriate_response_for_topic("racism")
            elif topic_analysis["contains_harassment"]:
                response_text = get_appropriate_response_for_topic("harassment")
            elif topic_analysis["contains_discrimination"]:
                response_text = get_appropriate_response_for_topic("discrimination")
            elif topic_analysis["contains_stress"]:
                response_text = get_appropriate_response_for_topic("stress")
            elif topic_analysis["contains_conflict"]:
                response_text = get_appropriate_response_for_topic("conflict")
            else:
                # Réponse générique pour les autres sujets sensibles
                response_text = get_appropriate_response_for_topic("")

        result = {
            "response": response_text,
            "detected_signals": [signal for signal in DISTRESS_SIGNALS if signal.lower() in message.lower()],
            "violent_words": violent_words,
            "violent_words_count": len(violent_words),
            "scopeflag": scopeflag
        }
    except Exception as e:
        # En cas d'erreur, revenir à une réponse simple sans analyse des mots violents
        logger.error(f"Error in OpenAI API call: {str(e)}")
        fallback_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )

        result = {
            "response": fallback_response.choices[0].message.content,
            "detected_signals": [signal for signal in DISTRESS_SIGNALS if signal.lower() in message.lower()],
            "violent_words": [],
            "violent_words_count": 0,
            "scopeflag": False,
            "error": str(e)
        }

    # Analyse des thématiques et mise à jour des statistiques si un employé est spécifié
    if employee_id:
        try:
            employee = Employee.objects.get(id=employee_id)

            # Prétraitement du texte pour le comptage total des mots
            words = preprocess_text(message)
            total_words = len(words)

            # Mise à jour des statistiques de l'employé
            employee.total_words_count += total_words

            # Seulement incrémenter le compteur de mots violents si le message est dans le sujet (scopeflag = False)
            if not result.get("scopeflag", False) and violent_words:
                employee.violent_words_count += len(violent_words)

                # Enregistrement des mots violents seulement si dans le sujet
                for word in violent_words:
                    ViolentWord.objects.create(
                        employee=employee,
                        word=word
                    )

            employee.save()

            # Analyse des thématiques
            themes = PsychologicalTheme.objects.all()
            detected_themes = []

            # Détection simple des thématiques par présence du nom
            text_lower = message.lower()
            for theme in themes:
                if theme.name.lower() in text_lower:
                    detected_themes.append(theme)

            # Mise à jour des compteurs de thématiques seulement si dans le sujet
            if not result.get("scopeflag", False) and detected_themes:
                for theme in detected_themes:
                    counter, created = EmployeeThemeCounter.objects.get_or_create(
                        employee=employee,
                        theme=theme,
                        defaults={'count': 0}
                    )
                    counter.count = F('count') + 1
                    counter.save()

            # Ajouter les résultats de l'analyse au résultat final
            result.update({
                "total_words": total_words,
                "detected_themes": [theme.name for theme in detected_themes]
            })

        except Employee.DoesNotExist:
            result.update({"error": "Employé non trouvé"})

    return result
