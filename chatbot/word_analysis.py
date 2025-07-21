"""
Module pour l'analyse des mots violents et des thématiques psychologiques
"""
import re
from typing import List, Dict, Tuple
from django.db.models import F
import openai
import os
from dotenv import load_dotenv
from .models import Employee, ViolentWord, PsychologicalTheme, EmployeeThemeCounter

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client OpenAI
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

def analyze_violent_content(message: str) -> Dict:
    """
    Utilise l'API OpenAI pour analyser si le message contient des mots violents
    
    Args:
        message (str): Le message à analyser
        
    Returns:
        Dict: Résultat de l'analyse avec les mots violents détectés
    """
    prompt = """
    Analysez le message suivant et identifiez tous les mots ou expressions qui pourraient indiquer de la violence, 
    de la détresse psychologique, de l'anxiété, du stress, ou d'autres problèmes de santé mentale dans un contexte professionnel.
    
    Retournez uniquement une liste des mots ou expressions identifiés, un par ligne.
    Si aucun mot violent ou indiquant de la détresse n'est détecté, retournez "AUCUN".
    
    Message à analyser : 
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Vous êtes un assistant spécialisé dans l'analyse de texte pour détecter des signes de détresse psychologique et de violence verbale."},
            {"role": "user", "content": prompt + message}
        ],
        temperature=0.3
    )
    
    # Extraire la réponse
    analysis_text = response.choices[0].message.content.strip()
    
    # Traiter la réponse
    if "AUCUN" in analysis_text:
        violent_words = []
    else:
        # Diviser la réponse en lignes et nettoyer
        violent_words = [word.strip() for word in analysis_text.split('\n') if word.strip()]
    
    return {
        'violent_words': violent_words,
        'violent_words_count': len(violent_words)
    }

def analyze_themes(text: str, themes: List[PsychologicalTheme]) -> List[PsychologicalTheme]:
    """
    Analyse le texte pour détecter les thématiques psychologiques
    
    Args:
        text (str): Texte à analyser
        themes (List[PsychologicalTheme]): Liste des thématiques à détecter
        
    Returns:
        List[PsychologicalTheme]: Liste des thématiques détectées
    """
    detected_themes = []
    text = text.lower()
    
    for theme in themes:
        # Si le nom de la thématique est présent dans le texte
        if theme.name.lower() in text:
            detected_themes.append(theme)
    
    return detected_themes

def process_message(employee: Employee, message: str) -> Dict:
    """
    Traite un message d'un employé pour détecter les mots violents et les thématiques
    
    Args:
        employee (Employee): L'employé qui a envoyé le message
        message (str): Le message à analyser
        
    Returns:
        Dict: Résultats de l'analyse
    """
    # Prétraitement du texte pour le comptage total des mots
    words = preprocess_text(message)
    total_words = len(words)
    
    # Analyse des mots violents via API
    violent_analysis = analyze_violent_content(message)
    violent_words = violent_analysis['violent_words']
    violent_words_count = violent_analysis['violent_words_count']
    
    # Mise à jour des statistiques de l'employé
    employee.total_words_count += total_words
    employee.violent_words_count += violent_words_count
    employee.save()
    
    # Enregistrement des mots violents
    for word in violent_words:
        ViolentWord.objects.create(
            employee=employee,
            word=word
        )
    
    # Analyse des thématiques
    themes = PsychologicalTheme.objects.all()
    detected_themes = analyze_themes(message, themes)
    
    # Mise à jour des compteurs de thématiques
    for theme in detected_themes:
        counter, created = EmployeeThemeCounter.objects.get_or_create(
            employee=employee,
            theme=theme,
            defaults={'count': 0}
        )
        counter.count = F('count') + 1
        counter.save()
    
    return {
        'total_words': total_words,
        'violent_words': violent_words,
        'violent_words_count': violent_words_count,
        'detected_themes': [theme.name for theme in detected_themes]
    }

def initialize_themes():
    """
    Initialise les thématiques psychologiques dans la base de données
    """
    themes = [
        {"name": "Harcèlement", "description": "Comportements répétés visant à dégrader les conditions de travail"},
        {"name": "Dépression", "description": "Trouble mental caractérisé par une tristesse persistante"},
        {"name": "Burnout", "description": "Syndrome d'épuisement professionnel"},
        {"name": "Stress", "description": "Réaction du corps face à une pression excessive"},
        {"name": "Anxiété", "description": "Sentiment d'inquiétude, de nervosité ou de peur"},
        {"name": "Conflit", "description": "Opposition entre personnes ou groupes dans l'entreprise"},
        {"name": "Discrimination", "description": "Traitement inégal basé sur certains critères"},
        {"name": "Surcharge", "description": "Excès de travail ou de responsabilités"},
        {"name": "Pression", "description": "Contraintes imposées pour atteindre des objectifs"},
        {"name": "Isolement", "description": "Sentiment d'être mis à l'écart dans l'environnement professionnel"},
        {"name": "Intimidation", "description": "Comportement visant à faire peur ou à dominer"},
        {"name": "Épuisement", "description": "État de fatigue extrême, physique ou émotionnelle"},
        {"name": "Mobbing", "description": "Harcèlement moral collectif"},
        {"name": "Violence", "description": "Comportements agressifs ou abusifs"},
        {"name": "Maltraitance", "description": "Mauvais traitements infligés dans le cadre professionnel"},
    ]
    
    for theme_data in themes:
        PsychologicalTheme.objects.get_or_create(
            name=theme_data["name"],
            defaults={"description": theme_data["description"]}
        )
