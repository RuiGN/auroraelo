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

        memberships_map = {
            "admin@auroraelo.com.br": ClinicMembership.Role.CLINIC_ADMIN,
            "dr.marcelo@auroraelo.com.br": ClinicMembership.Role.THERAPIST,
            "dra.camila@auroraelo.com.br": ClinicMembership.Role.THERAPIST,
            "enfermagem@auroraelo.com.br": ClinicMembership.Role.ADMINISTRATIVE_STAFF,
            "recepcao@auroraelo.com.br": ClinicMembership.Role.ADMINISTRATIVE_STAFF,
            "paciente.thiago@auroraelo.com.br": ClinicMembership.Role.PATIENT,
        }

        admin_user = User.objects.filter(email="admin@auroraelo.com.br").first()

        for email, role in memberships_map.items():
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(self.style.WARNING(f"Usuário {email} não encontrado no banco."))
                continue

            membership = ClinicMembership.infrastructure_objects.filter(
                user=user,
                clinic=clinic,
            ).first()

            if not membership:
                ClinicMembership.infrastructure_objects.create(
                    user=user,
                    clinic=clinic,
                    role=role,
                    authorized_by=admin_user,
                    is_active=True,
                    valid_from=date(2024, 1, 1),
                    valid_until=None,
                )
                self.stdout.write(self.style.SUCCESS(f"✓ Vínculo criado: {user.email} -> {role}"))
            else:
                membership.is_active = True
                membership.role = role
                membership.valid_from = date(2024, 1, 1)
                membership.valid_until = None
                membership.save(update_fields=["is_active", "role", "valid_from", "valid_until"])
                self.stdout.write(f"✓ Vínculo atualizado: {user.email} -> {role}")

        self.stdout.write(self.style.SUCCESS("✓ Clínica Aurora Elo e todos os vínculos configurados com sucesso!"))
