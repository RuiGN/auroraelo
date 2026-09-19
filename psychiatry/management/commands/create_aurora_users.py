"""Idempotent user creation command for Aurora Elo Health Systems.

Creates and initializes users for all clinical and administrative roles.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create staff, clinical, and demo patient user accounts for Aurora Elo."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Criando contas de acesso para todas as áreas..."))

        users_to_create = [
            {
                "email": "admin@auroraelo.com.br",
                "first_name": "Administrador",
                "last_name": "Geral TI",
                "password": "Aurora@Admin2026!",
                "is_staff": True,
                "is_superuser": True,
                "role_desc": "Administração do Sistema & Superusuário",
            },
            {
                "email": "dr.marcelo@auroraelo.com.br",
                "first_name": "Dr. Marcelo",
                "last_name": "Arantes",
                "password": "Aurora@Med2026!",
                "is_staff": True,
                "is_superuser": False,
                "role_desc": "Diretoria Médica & Psiquiatra Especialista em Adictologia",
            },
            {
                "email": "dra.camila@auroraelo.com.br",
                "first_name": "Dra. Camila",
                "last_name": "Mendonça",
                "password": "Aurora@Psi2026!",
                "is_staff": True,
                "is_superuser": False,
                "role_desc": "Psicóloga Clínica & Terapeuta dos 12 Passos",
            },
            {
                "email": "enfermagem@auroraelo.com.br",
                "first_name": "Equipe",
                "last_name": "Enfermagem 24h",
                "password": "Aurora@Enf2026!",
                "is_staff": True,
                "is_superuser": False,
                "role_desc": "Enfermagem Psiquiátrica & Plantão SOS Leitos",
            },
            {
                "email": "recepcao@auroraelo.com.br",
                "first_name": "Recepção",
                "last_name": "Aurora Elo",
                "password": "Aurora@Rec2026!",
                "is_staff": True,
                "is_superuser": False,
                "role_desc": "Recepção, Triagem & Admissão de Pacientes",
            },
            {
                "email": "paciente.thiago@auroraelo.com.br",
                "first_name": "Thiago",
                "last_name": "Mendonça",
                "password": "Aurora@Pac2026!",
                "is_staff": False,
                "is_superuser": False,
                "role_desc": "Paciente Acolhido (Recuperação Jogos de Azar / 12 Passos)",
            },
        ]

        for u in users_to_create:
            email = u["email"]
            user = User.objects.filter(email=email).first()
            if not user:
                user = User(
                    email=email,
                    username=email,
                    first_name=u["first_name"],
                    last_name=u["last_name"],
                    is_staff=u["is_staff"],
                    is_superuser=u["is_superuser"],
                    is_active=True,
                )
                user.set_password(u["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"✓ Usuário criado: {email} ({u['role_desc']})"))
            else:
                user.set_password(u["password"])
                user.is_staff = u["is_staff"]
                user.is_superuser = u["is_superuser"]
                user.is_active = True
                user.save()
                self.stdout.write(self.style.WARNING(f"• Usuário atualizado com nova senha: {email}"))

        self.stdout.write(self.style.SUCCESS("✓ Todas as contas de acesso criadas com sucesso!"))
