"""Provision primary Aurora Elo Clinic and link user memberships."""

from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from clinics.models import Clinic, ClinicConfiguration, ClinicMembership

User = get_user_model()


class Command(BaseCommand):
    help = "Provision the primary Aurora Elo Clinic and assign memberships to users."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Provisionando Clínica Aurora Elo..."))

        clinic = Clinic.infrastructure_objects.filter(slug="aurora-elo").first()
        if not clinic:
            clinic = Clinic.infrastructure_objects.create(
                name="Clínica Psiquiátrica Aurora Elo",
                slug="aurora-elo",
                is_active=True,
                is_demo=False,
            )
            self.stdout.write(self.style.SUCCESS(f"✓ Clínica criada: {clinic.name} ({clinic.slug})"))
        else:
            clinic.is_active = True
            clinic.save(update_fields=["is_active"])
            self.stdout.write(f"✓ Clínica existente confirmada ativa: {clinic.name}")

        config = ClinicConfiguration.infrastructure_objects.filter(clinic=clinic).first()
        if not config:
            config = ClinicConfiguration.infrastructure_objects.create(
                clinic=clinic,
                legal_name="Aurora Elo Psiquiatria Integrada Ltda",
                display_name="Clínica Aurora Elo",
                registration_identifier="12.345.678/0001-90",
                administrative_email="admin@auroraelo.com.br",
                administrative_phone="+55 11 3200-4130",
                address_line_1="Av. Paulista, 1000 - Bela Vista",
                city="São Paulo",
                region="SP",
                postal_code="01310-100",
                country_code="BR",
            )
            self.stdout.write(self.style.SUCCESS("✓ Configuração institucional da clínica criada."))
        else:
            self.stdout.write("✓ Configuração institucional já vinculada.")

        user_specs = [
            # Primary (.com.br)
            {"email": "admin@auroraelo.com.br", "first": "Administrador", "last": "Geral", "role": ClinicMembership.Role.CLINIC_ADMIN, "staff": True, "super": True},
            {"email": "dr.marcelo@auroraelo.com.br", "first": "Marcelo", "last": "Arantes", "role": ClinicMembership.Role.THERAPIST, "staff": True, "super": False},
            {"email": "dra.camila@auroraelo.com.br", "first": "Camila", "last": "Albuquerque", "role": ClinicMembership.Role.THERAPIST, "staff": True, "super": False},
            {"email": "recepcao@auroraelo.com.br", "first": "Recepção", "last": "Clínica", "role": ClinicMembership.Role.ADMINISTRATIVE_STAFF, "staff": True, "super": False},
            {"email": "enfermagem@auroraelo.com.br", "first": "Equipe", "last": "Enfermagem", "role": ClinicMembership.Role.ADMINISTRATIVE_STAFF, "staff": True, "super": False},
            {"email": "paciente.thiago@auroraelo.com.br", "first": "Thiago", "last": "Silva", "role": ClinicMembership.Role.PATIENT, "staff": False, "super": False},
            {"email": "paciente@auroraelo.com.br", "first": "Thiago", "last": "Silva", "role": ClinicMembership.Role.PATIENT, "staff": False, "super": False},

            # Aliases (.med.br)
            {"email": "admin@auroraelo.med.br", "first": "Administrador", "last": "Geral", "role": ClinicMembership.Role.CLINIC_ADMIN, "staff": True, "super": True},
            {"email": "dr.marcelo@auroraelo.med.br", "first": "Marcelo", "last": "Arantes", "role": ClinicMembership.Role.THERAPIST, "staff": True, "super": False},
            {"email": "dra.camila@auroraelo.med.br", "first": "Camila", "last": "Albuquerque", "role": ClinicMembership.Role.THERAPIST, "staff": True, "super": False},
            {"email": "recepcao@auroraelo.med.br", "first": "Recepção", "last": "Clínica", "role": ClinicMembership.Role.ADMINISTRATIVE_STAFF, "staff": True, "super": False},
            {"email": "enfermagem@auroraelo.med.br", "first": "Equipe", "last": "Enfermagem", "role": ClinicMembership.Role.ADMINISTRATIVE_STAFF, "staff": True, "super": False},
            {"email": "paciente@auroraelo.med.br", "first": "Thiago", "last": "Silva", "role": ClinicMembership.Role.PATIENT, "staff": False, "super": False},
        ]

        admin_user = User.objects.filter(email="admin@auroraelo.com.br").first()

        for spec in user_specs:
            user = User.objects.filter(email=spec["email"]).first()
            if not user:
                user = User.objects.create_user(
                    email=spec["email"],
                    password="AuroraElo@2026!",
                    first_name=spec["first"],
                    last_name=spec["last"],
                    is_staff=spec["staff"],
                    is_superuser=spec["super"],
                    is_active=True,
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Usuário criado: {user.email}"))
            else:
                user.set_password("AuroraElo@2026!")
                user.first_name = spec["first"]
                user.last_name = spec["last"]
                user.is_staff = spec["staff"]
                user.is_superuser = spec["super"]
                user.is_active = True
                user.save()
                self.stdout.write(f"✓ Credenciais e dados atualizados: {user.email}")

            if not admin_user and user.is_superuser:
                admin_user = user

            membership = ClinicMembership.infrastructure_objects.filter(
                user=user,
                clinic=clinic,
            ).first()

            if not membership:
                ClinicMembership.infrastructure_objects.create(
                    user=user,
                    clinic=clinic,
                    role=spec["role"],
                    authorized_by=admin_user or user,
                    is_active=True,
                    valid_from=date(2024, 1, 1),
                    valid_until=None,
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Vínculo criado: {user.email} -> {spec['role']}"))
            else:
                membership.is_active = True
                membership.role = spec["role"]
                membership.valid_from = date(2024, 1, 1)
                membership.valid_until = None
                membership.save(update_fields=["is_active", "role", "valid_from", "valid_until"])
                self.stdout.write(f"✓ Vínculo atualizado: {user.email} -> {spec['role']}")

        self.stdout.write(self.style.SUCCESS("✓ Clínica Aurora Elo e todos os usuários/vínculos configurados com sucesso!"))
