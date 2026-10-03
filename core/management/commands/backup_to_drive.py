"""
Management command para backup criptografado do banco de dados (SaaS)
Faz o pg_dump, compacta, aplica criptografia simétrica e envia para o Google Drive.
"""

import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class Command(BaseCommand):
    help = "Realiza backup do banco, criptografa e faz upload para o Google Drive"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando rotina de backup de segurança..."))
        
        # 1. Obter configs do banco de dados
        db_config = settings.DATABASES.get('default', {})
        db_name = db_config.get('NAME')
        db_user = db_config.get('USER')
        db_pass = db_config.get('PASSWORD')
        db_host = db_config.get('HOST', '127.0.0.1')
        db_port = db_config.get('PORT', '5432')
        
        if not all([db_name, db_user, db_host]):
            raise CommandError("Configurações do banco de dados incompletas.")
            
        # 2. Configurar chaves e credenciais
        drive_creds_path = getattr(settings, 'GOOGLE_DRIVE_CREDENTIALS_PATH', None)
        encryption_key_b64 = getattr(settings, 'BACKUP_ENCRYPTION_KEY', None)
        drive_folder_id = getattr(settings, 'GOOGLE_DRIVE_BACKUP_FOLDER_ID', None)
        
        if not drive_creds_path or not os.path.exists(drive_creds_path):
            self.stdout.write(self.style.WARNING("Aviso: GOOGLE_DRIVE_CREDENTIALS_PATH não configurado ou arquivo não encontrado. O upload para o GDrive será pulado."))
        if not encryption_key_b64:
            self.stdout.write(self.style.WARNING("Aviso: BACKUP_ENCRYPTION_KEY não configurada. Arquivo NÃO será criptografado."))
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"auroraelo_backup_{timestamp}"
        dump_file = f"/tmp/{filename_base}.sql"
        gz_file = f"{dump_file}.gz"
        enc_file = f"{gz_file}.enc"
        
        final_file = enc_file if encryption_key_b64 else gz_file
        
        try:
            # 3. Fazer o pg_dump
            self.stdout.write("1/4. Executando pg_dump...")
            env = os.environ.copy()
            if db_pass:
                env['PGPASSWORD'] = db_pass
                
            cmd_dump = [
                "pg_dump",
                "-h", db_host,
                "-p", str(db_port),
                "-U", db_user,
                "-F", "p", # plain text format
                "-f", dump_file,
                db_name
            ]
            
            subprocess.run(cmd_dump, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 4. Compactar o arquivo
            self.stdout.write("2/4. Compactando o dump (gzip)...")
            subprocess.run(["gzip", "-f", dump_file], check=True)
            
            # 5. Criptografar
            if encryption_key_b64:
                self.stdout.write("3/4. Criptografando o arquivo (Fernet)...")
                fernet = Fernet(encryption_key_b64)
                with open(gz_file, 'rb') as f_in:
                    data = f_in.read()
                encrypted = fernet.encrypt(data)
                with open(enc_file, 'wb') as f_out:
                    f_out.write(encrypted)
                os.remove(gz_file) # Apagar o gzip em texto claro
            else:
                self.stdout.write("3/4. Pulando criptografia (Chave não configurada)...")
                
            # 6. Upload GDrive
            if drive_creds_path and os.path.exists(drive_creds_path):
                self.stdout.write("4/4. Fazendo upload para o Google Drive...")
                SCOPES = ['https://www.googleapis.com/auth/drive.file']
                creds = service_account.Credentials.from_service_account_file(
                    drive_creds_path, scopes=SCOPES
                )
                service = build('drive', 'v3', credentials=creds)
                
                file_metadata = {'name': os.path.basename(final_file)}
                if drive_folder_id:
                    file_metadata['parents'] = [drive_folder_id]
                    
                media = MediaFileUpload(final_file, resumable=True)
                
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                self.stdout.write(self.style.SUCCESS(f"Upload concluído! ID do arquivo: {file.get('id')}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Backup gerado localmente em: {final_file}"))
                
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"Erro ao executar comando do sistema: {e.stderr.decode()}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ocorreu um erro durante o backup: {str(e)}"))
        finally:
            # Limpeza
            self.stdout.write("Limpando arquivos temporários locais...")
            for f in [dump_file, gz_file, enc_file]:
                if os.path.exists(f) and f != final_file:
                    os.remove(f)
                    
            self.stdout.write(self.style.SUCCESS("Rotina de backup finalizada com sucesso!"))
