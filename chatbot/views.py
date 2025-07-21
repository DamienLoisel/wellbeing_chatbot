"""
Vues Django pour le chatbot de soutien psychologique
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import analyze_message
from .models import Employee, PsychologicalTheme
import json

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

def index(request):
    """Vue pour la page d'accueil du chatbot"""
    # Initialiser les thématiques si nécessaire
    if PsychologicalTheme.objects.count() == 0:
        initialize_themes()
    
    # Récupérer ou créer un employé pour la démonstration
    # Dans une application réelle, vous utiliseriez l'authentification
    employee, created = Employee.objects.get_or_create(
        first_name="Utilisateur",
        last_name="Test",
        defaults={
            'birth_date': '1990-01-01'
        }
    )
    
    return render(request, 'chat.html', {'employee_id': employee.id})

@csrf_exempt
def chat(request):
    """
    API pour le traitement des messages du chatbot
    
    Cette vue est exemptée de la protection CSRF pour permettre les requêtes AJAX
    depuis le frontend. Dans un environnement de production, il faudrait implémenter
    une meilleure gestion de la sécurité.
    """
    if request.method == 'POST':
        try:
            message = request.POST.get('message', '')
            employee_id = request.POST.get('employee_id')
            
            # Analyser le message avec l'ID de l'employé si disponible
            if employee_id and employee_id.isdigit():
                analysis = analyze_message(message, int(employee_id))
            else:
                analysis = analyze_message(message)
            
            return JsonResponse(analysis)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def employee_stats(request, employee_id):
    """Vue pour afficher les statistiques d'un employé"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Récupérer les mots violents les plus récents
    recent_violent_words = employee.violent_words.order_by('-timestamp')[:10]
    
    # Récupérer les compteurs de thématiques
    theme_counters = employee.theme_counters.select_related('theme').all()
    
    context = {
        'employee': employee,
        'violent_words_ratio': employee.violent_words_ratio * 100,  # Convert to percentage
        'recent_violent_words': recent_violent_words,
        'theme_counters': theme_counters,
    }
    
    return render(request, 'employee_stats.html', context)
