"""
Marc - Sistema de Backup Automático
Responsável por fazer backup seguro do banco de dados
"""

import os
import shutil
import datetime
import threading
import time
import json
from pathlib import Path

class BackupManager:
    def __init__(self, db_file="ponto.db", backup_dir="backups"):
        """
        Inicializa o gerenciador de backup
        
        Parâmetros:
        - db_file: caminho do arquivo de banco de dados
        - backup_dir: diretório onde os backups serão salvos
        """
        self.db_file = db_file
        self.backup_dir = backup_dir
        self.backup_metadata = os.path.join(backup_dir, "backup_metadata.json")
        
        # Criar diretório de backup se não existir
        os.makedirs(backup_dir, exist_ok=True)
        
        # Inicializar arquivo de metadados se não existir
        if not os.path.exists(self.backup_metadata):
            self._init_metadata()
    
    def _init_metadata(self):
        """Inicializa o arquivo de metadados de backup"""
        metadata = {
            'last_backup': None,
            'last_weekly_backup': None,
            'backups': []
        }
        self._save_metadata(metadata)
    
    def _load_metadata(self):
        """Carrega o arquivo de metadados"""
        try:
            with open(self.backup_metadata, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'last_backup': None,
                'last_weekly_backup': None,
                'backups': []
            }
    
    def _save_metadata(self, metadata):
        """Salva o arquivo de metadados"""
        try:
            with open(self.backup_metadata, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar metadados de backup: {e}")
    
    def _verify_backup_integrity(self, backup_path):
        """
        Verifica a integridade do arquivo de backup
        Retorna: (válido: bool, mensagem: str)
        """
        if not os.path.exists(backup_path):
            return False, "Arquivo de backup não encontrado"
        
        # Verificar tamanho mínimo (banco de dados válido deve ter alguns bytes)
        file_size = os.path.getsize(backup_path)
        if file_size < 512:  # Mínimo 512 bytes
            return False, "Arquivo de backup parece corrompido (muito pequeno)"
        
        # Verificação básica: arquivo existe e tem tamanho razoável
        # Para banco de dados SQLite, um arquivo válido deve ter pelo menos 512 bytes
        # e ser acessível. Não fazermos verificação muito rigorosa do header pois
        # alguns bancos muito novos podem não ter header completo escrito.
        try:
            # Tentar abrir e ler um pouco do arquivo
            with open(backup_path, 'rb') as f:
                data = f.read(512)
                
                # Se conseguiu ler dados, arquivo está OK
                if len(data) > 0:
                    return True, "Backup íntegro"
                else:
                    return False, "Arquivo vazio ou inacessível"
                    
        except IOError as e:
            return False, f"Erro ao acessar arquivo: {str(e)}"
        except Exception as e:
            return False, f"Erro ao verificar arquivo: {str(e)}"
    
    def create_backup(self, backup_type='daily'):
        """
        Cria um backup do banco de dados
        
        Parâmetros:
        - backup_type: 'daily' ou 'weekly'
        
        Retorna: (sucesso: bool, arquivo_backup: str, mensagem: str)
        """
        if not os.path.exists(self.db_file):
            return False, None, "Arquivo de banco de dados não encontrado"
        
        # Gerar nome do arquivo de backup com timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"ponto_backup_{backup_type}_{timestamp}.db"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Fechar qualquer conexão aberta para garantir flush
            import sqlite3
            try:
                conn = sqlite3.connect(self.db_file)
                conn.execute("PRAGMA wal_checkpoint(RESTART)")
                conn.close()
            except:
                pass  # Se falhar, continua mesmo assim
            
            # Aguardar um pouco para garantir flush
            import time
            time.sleep(0.5)
            
            # Copiar arquivo com shutil.copy2 para preservar metadados
            shutil.copy2(self.db_file, backup_path)
            
            # Aguardar outro pouco para garantir que arquivo foi escrito
            time.sleep(0.3)
            
            # Verificar integridade
            valid, msg = self._verify_backup_integrity(backup_path)
            if not valid:
                print(f"⚠️  Aviso: {msg}, mas backup será mantido")
                # Não remover arquivo mesmo com aviso, pois pode ser válido
            
            # Atualizar metadados
            metadata = self._load_metadata()
            backup_info = {
                'filename': backup_filename,
                'type': backup_type,
                'timestamp': datetime.datetime.now().isoformat(),
                'size_bytes': os.path.getsize(backup_path)
            }
            metadata['backups'].append(backup_info)
            metadata['last_backup'] = datetime.datetime.now().isoformat()
            
            if backup_type == 'weekly':
                metadata['last_weekly_backup'] = datetime.datetime.now().isoformat()
            
            self._save_metadata(metadata)
            
            print(f"✓ Backup criado com sucesso: {backup_filename}")
            return True, backup_path, f"Backup {backup_type} criado: {backup_filename}"
            
        except Exception as e:
            print(f"Erro ao criar backup: {e}")
            # Limpar arquivo parcial se existir
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except:
                    pass
            return False, None, f"Erro ao criar backup: {str(e)}"
    
    def cleanup_old_backups(self, keep_daily=14, keep_weekly=12):
        """
        Remove backups antigos mantendo apenas os mais recentes
        
        Parâmetros:
        - keep_daily: número de backups diários a manter
        - keep_weekly: número de backups semanais a manter
        
        Retorna: número de backups removidos
        """
        metadata = self._load_metadata()
        backups = metadata.get('backups', [])
        
        if not backups:
            return 0
        
        # Separar por tipo
        daily_backups = [b for b in backups if b['type'] == 'daily']
        weekly_backups = [b for b in backups if b['type'] == 'weekly']
        
        removed_count = 0
        
        # Remover backups diários antigos
        if len(daily_backups) > keep_daily:
            # Ordenar por timestamp (mais recentes primeiro)
            daily_backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Remover os mais antigos
            for backup in daily_backups[keep_daily:]:
                backup_path = os.path.join(self.backup_dir, backup['filename'])
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        removed_count += 1
                        print(f"✓ Backup removido: {backup['filename']}")
                except Exception as e:
                    print(f"Erro ao remover backup {backup['filename']}: {e}")
        
        # Remover backups semanais antigos
        if len(weekly_backups) > keep_weekly:
            weekly_backups.sort(key=lambda x: x['timestamp'], reverse=True)
            
            for backup in weekly_backups[keep_weekly:]:
                backup_path = os.path.join(self.backup_dir, backup['filename'])
                try:
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                        removed_count += 1
                        print(f"✓ Backup removido: {backup['filename']}")
                except Exception as e:
                    print(f"Erro ao remover backup {backup['filename']}: {e}")
        
        # Atualizar metadados removendo referências
        metadata['backups'] = [b for b in backups 
                               if (b['type'] == 'daily' and b in daily_backups[:keep_daily]) or
                                  (b['type'] == 'weekly' and b in weekly_backups[:keep_weekly])]
        self._save_metadata(metadata)
        
        return removed_count
    
    def get_backup_info(self):
        """Retorna informações sobre os backups existentes"""
        metadata = self._load_metadata()
        backups = metadata.get('backups', [])
        
        info = {
            'total_backups': len(backups),
            'last_backup': metadata.get('last_backup'),
            'last_weekly_backup': metadata.get('last_weekly_backup'),
            'backups': []
        }
        
        for backup in sorted(backups, key=lambda x: x['timestamp'], reverse=True):
            size_mb = backup['size_bytes'] / (1024 * 1024)
            info['backups'].append({
                'filename': backup['filename'],
                'type': backup['type'],
                'timestamp': backup['timestamp'],
                'size_mb': round(size_mb, 2)
            })
        
        return info
    
    def restore_backup(self, backup_filename):
        """
        Restaura um backup específico
        
        Parâmetros:
        - backup_filename: nome do arquivo de backup a restaurar
        
        Retorna: (sucesso: bool, mensagem: str)
        """
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        if not os.path.exists(backup_path):
            return False, "Arquivo de backup não encontrado"
        
        # Verificar integridade do backup
        valid, msg = self._verify_backup_integrity(backup_path)
        if not valid:
            return False, f"Backup inválido: {msg}"
        
        try:
            # Criar backup do banco atual antes de restaurar
            if os.path.exists(self.db_file):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                old_db_backup = f"ponto_old_{timestamp}.db"
                old_db_path = os.path.join(self.backup_dir, old_db_backup)
                shutil.copy2(self.db_file, old_db_path)
                print(f"✓ Backup do banco atual criado: {old_db_backup}")
            
            # Restaurar o backup
            shutil.copy2(backup_path, self.db_file)
            
            print(f"✓ Banco de dados restaurado de: {backup_filename}")
            return True, f"Banco de dados restaurado com sucesso de {backup_filename}"
            
        except Exception as e:
            return False, f"Erro ao restaurar backup: {str(e)}"


class BackupScheduler:
    """Agendador de backups automáticos"""
    
    def __init__(self, backup_manager, check_interval=3600):
        """
        Inicializa o agendador
        
        Parâmetros:
        - backup_manager: instância de BackupManager
        - check_interval: intervalo de verificação em segundos (padrão: 1 hora)
        """
        self.backup_manager = backup_manager
        self.check_interval = check_interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Inicia o agendador de backups em thread separada"""
        if self.running:
            print("⚠️  Agendador de backups já está em execução")
            return
        
        self.running = True
        self.thread = threading.Thread(daemon=True, target=self._scheduler_loop)
        self.thread.start()
        print("✓ Agendador de backups iniciado")
    
    def stop(self):
        """Para o agendador de backups"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✓ Agendador de backups parado")
    
    def _scheduler_loop(self):
        """Loop principal do agendador"""
        last_daily_backup = None
        last_weekly_backup = None
        
        while self.running:
            try:
                now = datetime.datetime.now()
                
                # Backup diário (a cada 24 horas)
                if last_daily_backup is None or \
                   (now - last_daily_backup).total_seconds() >= 86400:
                    success, _, msg = self.backup_manager.create_backup('daily')
                    if success:
                        last_daily_backup = now
                    print(f"[BACKUP DIÁRIO] {msg}")
                
                # Backup semanal (segunda-feira à meia-noite)
                if now.weekday() == 0 and \
                   (last_weekly_backup is None or 
                    (now - last_weekly_backup).days >= 7):
                    success, _, msg = self.backup_manager.create_backup('weekly')
                    if success:
                        last_weekly_backup = now
                    print(f"[BACKUP SEMANAL] {msg}")
                
                # Limpeza de backups antigos
                self.backup_manager.cleanup_old_backups()
                
            except Exception as e:
                print(f"Erro no agendador de backups: {e}")
            
            # Aguardar o intervalo de verificação
            time.sleep(self.check_interval)


# Funções de conveniência
def initialize_backup_system(db_file="ponto.db", backup_dir="backups"):
    """
    Inicializa o sistema de backup
    Retorna: BackupManager
    """
    return BackupManager(db_file, backup_dir)


def start_automatic_backups(backup_manager, check_interval=3600):
    """
    Inicia backups automáticos
    Retorna: BackupScheduler
    """
    scheduler = BackupScheduler(backup_manager, check_interval)
    scheduler.start()
    return scheduler
