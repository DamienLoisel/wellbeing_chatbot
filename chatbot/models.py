from django.db import models
from django.utils import timezone

# Create your models here.

class Employee(models.Model):
    """
    Modèle pour stocker les informations des employés et leur utilisation de mots violents
    """
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    birth_date = models.DateField(verbose_name="Date de naissance")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistiques sur les mots
    total_words_count = models.IntegerField(default=0, verbose_name="Nombre de mots total")
    violent_words_count = models.IntegerField(default=0, verbose_name="Nombre de mots violents")
    
    @property
    def violent_words_ratio(self):
        """Calcule le ratio de mots violents par rapport au nombre total de mots"""
        if self.total_words_count == 0:
            return 0
        return round(self.violent_words_count / self.total_words_count, 4)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"


class ViolentWord(models.Model):
    """
    Modèle pour stocker les occurrences de mots violents utilisés par les employés
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='violent_words')
    word = models.CharField(max_length=100, verbose_name="Mot violent")
    timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.word} ({self.employee})"
    
    class Meta:
        verbose_name = "Mot violent"
        verbose_name_plural = "Mots violents"


class PsychologicalTheme(models.Model):
    """
    Modèle pour définir les thématiques psychologiques à surveiller
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom de la thématique")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Thématique psychologique"
        verbose_name_plural = "Thématiques psychologiques"


class EmployeeThemeCounter(models.Model):
    """
    Modèle pour compter les occurrences de thématiques psychologiques par employé
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='theme_counters')
    theme = models.ForeignKey(PsychologicalTheme, on_delete=models.CASCADE)
    count = models.IntegerField(default=0, verbose_name="Nombre d'occurrences")
    
    class Meta:
        unique_together = ('employee', 'theme')
        verbose_name = "Compteur de thématique"
        verbose_name_plural = "Compteurs de thématiques"
    
    def __str__(self):
        return f"{self.employee} - {self.theme}: {self.count}"
