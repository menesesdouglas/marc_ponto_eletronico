import sqlite3
import datetime
import bcrypt

DB_FILE = "ponto.db"
DB_TIMEOUT = 10  # Timeout de 10 segundos para operações

def connect():
    """Retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect(DB_FILE, timeout=DB_TIMEOUT)
    # Habilitar timeout e retry automático
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging para melhor concorrência
    return conn

def init_db():
    """Inicializa o banco de dados com todas as tabelas necessárias"""
    conn = connect()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            tipo TEXT,
            timestamp TEXT,
            FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
        )
    ''')
    
    # Criar índice para melhorar performance de consultas
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_eventos_func_data 
        ON eventos(funcionario_id, DATE(timestamp))
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS feriados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT UNIQUE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS folgas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER,
            data TEXT,
            UNIQUE(funcionario_id, data),
            FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
        )
    ''')

    # TABELA: Usuários para autenticação
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    ''')

    # TABELA: Logs de auditoria
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            detalhes TEXT,
            ip_address TEXT,
            status TEXT DEFAULT 'sucesso'
        )
    ''')
    
    # Criar índices para melhorar consultas de logs
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
        ON logs(timestamp DESC)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_logs_categoria 
        ON logs(categoria, timestamp DESC)
    ''')

    conn.commit()
    
    # Criar usuários padrão se não existirem
    _create_default_users(conn)
    
    conn.close()

def _create_default_users(conn):
    """Cria usuários padrão (admin e funcionário) se não existirem"""
    c = conn.cursor()
    
    # Verificar se já existem usuários
    c.execute('SELECT COUNT(*) FROM usuarios')
    count = c.fetchone()[0]
    
    if count == 0:
        # Criar usuário admin
        admin_password = "admin123"
        admin_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
        
        c.execute('''
            INSERT INTO usuarios (username, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_hash.decode('utf-8'), 1, datetime.datetime.now().isoformat()))
        
        # Criar usuário funcionário
        func_password = "func123"
        func_hash = bcrypt.hashpw(func_password.encode('utf-8'), bcrypt.gensalt())
        
        c.execute('''
            INSERT INTO usuarios (username, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('funcionario', func_hash.decode('utf-8'), 0, datetime.datetime.now().isoformat()))
        
        conn.commit()
        print("✓ Usuários padrão criados: admin (admin123) e funcionario (func123)")

# --- Funções de auditoria ---
def log_action(usuario, acao, categoria, detalhes=None, ip_address=None, status='sucesso'):
    """
    Registra uma ação no log de auditoria
    
    Parâmetros:
    - usuario: nome do usuário que realizou a ação
    - acao: descrição da ação (ex: "Adicionou funcionário", "Removeu evento")
    - categoria: tipo de ação ("funcionario", "evento", "feriado", "folga", "usuario", "autenticacao")
    - detalhes: informações adicionais em formato texto
    - ip_address: endereço IP (opcional)
    - status: "sucesso" ou "falha"
    """
    try:
        conn = connect()
        c = conn.cursor()
        
        timestamp = datetime.datetime.now().isoformat()
        
        c.execute('''
            INSERT INTO logs (timestamp, usuario, acao, categoria, detalhes, ip_address, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, usuario, acao, categoria, detalhes, ip_address, status))
        
        conn.commit()
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"Erro ao registrar log: {e}")
        return False

def get_logs(limit=100, categoria=None, usuario=None, data_inicio=None, data_fim=None):
    """
    Recupera logs de auditoria com filtros opcionais
    
    Parâmetros:
    - limit: número máximo de registros
    - categoria: filtrar por categoria específica
    - usuario: filtrar por usuário específico
    - data_inicio: data inicial (datetime.date ou string ISO)
    - data_fim: data final (datetime.date ou string ISO)
    """
    try:
        conn = connect()
        c = conn.cursor()
        
        query = 'SELECT * FROM logs WHERE 1=1'
        params = []
        
        if categoria:
            query += ' AND categoria = ?'
            params.append(categoria)
        
        if usuario:
            query += ' AND usuario = ?'
            params.append(usuario)
        
        if data_inicio:
            if isinstance(data_inicio, datetime.date):
                data_inicio = data_inicio.isoformat()
            query += ' AND DATE(timestamp) >= ?'
            params.append(data_inicio)
        
        if data_fim:
            if isinstance(data_fim, datetime.date):
                data_fim = data_fim.isoformat()
            query += ' AND DATE(timestamp) <= ?'
            params.append(data_fim)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        
        logs = []
        for row in c.fetchall():
            logs.append({
                'id': row[0],
                'timestamp': row[1],
                'usuario': row[2],
                'acao': row[3],
                'categoria': row[4],
                'detalhes': row[5],
                'ip_address': row[6],
                'status': row[7]
            })
        
        conn.close()
        return logs
        
    except sqlite3.Error as e:
        print(f"Erro ao buscar logs: {e}")
        return []

def get_logs_summary(data_inicio=None, data_fim=None):
    """
    Retorna resumo estatístico dos logs
    """
    try:
        conn = connect()
        c = conn.cursor()
        
        query = 'SELECT categoria, status, COUNT(*) FROM logs WHERE 1=1'
        params = []
        
        if data_inicio:
            if isinstance(data_inicio, datetime.date):
                data_inicio = data_inicio.isoformat()
            query += ' AND DATE(timestamp) >= ?'
            params.append(data_inicio)
        
        if data_fim:
            if isinstance(data_fim, datetime.date):
                data_fim = data_fim.isoformat()
            query += ' AND DATE(timestamp) <= ?'
            params.append(data_fim)
        
        query += ' GROUP BY categoria, status'
        
        c.execute(query, params)
        
        summary = {}
        for row in c.fetchall():
            categoria, status, count = row
            if categoria not in summary:
                summary[categoria] = {'sucesso': 0, 'falha': 0}
            summary[categoria][status] = count
        
        conn.close()
        return summary
        
    except sqlite3.Error as e:
        print(f"Erro ao gerar resumo de logs: {e}")
        return {}

def clear_old_logs(days=90):
    """
    Remove logs mais antigos que X dias (para manutenção)
    Retorna: número de registros removidos
    """
    try:
        conn = connect()
        c = conn.cursor()
        
        cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        c.execute('SELECT COUNT(*) FROM logs WHERE timestamp < ?', (cutoff_date,))
        count = c.fetchone()[0]
        
        c.execute('DELETE FROM logs WHERE timestamp < ?', (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        print(f"✓ {count} logs removidos (anteriores a {cutoff_date[:10]})")
        return count
        
    except sqlite3.Error as e:
        print(f"Erro ao limpar logs antigos: {e}")
        return 0

# --- Funções de autenticação ---
def authenticate_user(username, password):
    """
    Autentica usuário verificando username e senha
    Retorna: (sucesso: bool, is_admin: bool, mensagem: str)
    """
    try:
        conn = connect()
        c = conn.cursor()
        
        c.execute('''
            SELECT id, password_hash, is_admin 
            FROM usuarios 
            WHERE username = ?
        ''', (username,))
        
        result = c.fetchone()
        
        if not result:
            conn.close()
            # Log de falha de autenticação
            log_action(username, "Tentativa de login - usuário não encontrado", "autenticacao", 
                      status='falha')
            return False, False, "Usuário não encontrado"
        
        user_id, password_hash, is_admin = result
        
        # Verificar senha usando bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            # Atualizar último login
            c.execute('''
                UPDATE usuarios 
                SET last_login = ? 
                WHERE id = ?
            ''', (datetime.datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
            
            # Log de login bem-sucedido
            log_action(username, "Login realizado com sucesso", "autenticacao",
                      detalhes=f"Tipo: {'Admin' if is_admin else 'Funcionário'}")
            
            return True, bool(is_admin), "Login realizado com sucesso"
        else:
            conn.close()
            # Log de senha incorreta
            log_action(username, "Tentativa de login - senha incorreta", "autenticacao",
                      status='falha')
            return False, False, "Senha incorreta"
            
    except sqlite3.Error as e:
        print(f"Erro ao autenticar: {e}")
        log_action(username, f"Erro na autenticação: {str(e)}", "autenticacao",
                  status='falha')
        return False, False, f"Erro no banco de dados: {str(e)}"

def create_user(username, password, is_admin=False, created_by='system'):
    """
    Cria um novo usuário no sistema
    Retorna: (sucesso: bool, mensagem: str)
    """
    if not username or not username.strip():
        return False, "Nome de usuário não pode estar vazio"
    
    if not password or len(password) < 6:
        return False, "Senha deve ter no mínimo 6 caracteres"
    
    try:
        conn = connect()
        c = conn.cursor()
        
        # Verificar se usuário já existe
        c.execute('SELECT id FROM usuarios WHERE username = ?', (username,))
        if c.fetchone():
            conn.close()
            log_action(created_by, f"Tentativa de criar usuário duplicado: {username}", "usuario",
                      status='falha')
            return False, "Nome de usuário já existe"
        
        # Criar hash da senha
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Inserir usuário
        c.execute('''
            INSERT INTO usuarios (username, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash.decode('utf-8'), int(is_admin), datetime.datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        # Log de criação de usuário
        log_action(created_by, f"Criou usuário: {username}", "usuario",
                  detalhes=f"Tipo: {'Admin' if is_admin else 'Funcionário'}")
        
        return True, "Usuário criado com sucesso"
        
    except sqlite3.Error as e:
        print(f"Erro ao criar usuário: {e}")
        log_action(created_by, f"Erro ao criar usuário {username}: {str(e)}", "usuario",
                  status='falha')
        return False, f"Erro no banco de dados: {str(e)}"

def change_password(username, old_password, new_password):
    """
    Altera a senha de um usuário
    Retorna: (sucesso: bool, mensagem: str)
    """
    if not new_password or len(new_password) < 6:
        return False, "Nova senha deve ter no mínimo 6 caracteres"
    
    try:
        conn = connect()
        c = conn.cursor()
        
        # Buscar usuário
        c.execute('''
            SELECT id, password_hash 
            FROM usuarios 
            WHERE username = ?
        ''', (username,))
        
        result = c.fetchone()
        
        if not result:
            conn.close()
            log_action(username, "Tentativa de alterar senha - usuário não encontrado", "usuario",
                      status='falha')
            return False, "Usuário não encontrado"
        
        user_id, password_hash = result
        
        # Verificar senha antiga
        if not bcrypt.checkpw(old_password.encode('utf-8'), password_hash.encode('utf-8')):
            conn.close()
            log_action(username, "Tentativa de alterar senha - senha atual incorreta", "usuario",
                      status='falha')
            return False, "Senha atual incorreta"
        
        # Criar hash da nova senha
        new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Atualizar senha
        c.execute('''
            UPDATE usuarios 
            SET password_hash = ? 
            WHERE id = ?
        ''', (new_password_hash.decode('utf-8'), user_id))
        
        conn.commit()
        conn.close()
        
        # Log de alteração de senha
        log_action(username, "Alterou a própria senha", "usuario")
        
        return True, "Senha alterada com sucesso"
        
    except sqlite3.Error as e:
        print(f"Erro ao alterar senha: {e}")
        log_action(username, f"Erro ao alterar senha: {str(e)}", "usuario",
                  status='falha')
        return False, f"Erro no banco de dados: {str(e)}"

def list_users():
    """Lista todos os usuários (sem mostrar senhas)"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('''
            SELECT id, username, is_admin, created_at, last_login 
            FROM usuarios 
            ORDER BY username
        ''')
        
        users = []
        for row in c.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'is_admin': bool(row[2]),
                'created_at': row[3],
                'last_login': row[4]
            })
        
        conn.close()
        return users
        
    except sqlite3.Error as e:
        print(f"Erro ao listar usuários: {e}")
        return []

def delete_user(username, deleted_by='admin'):
    """
    Remove um usuário do sistema
    Retorna: (sucesso: bool, mensagem: str)
    """
    if username in ['admin', 'funcionario']:
        log_action(deleted_by, f"Tentativa de remover usuário padrão: {username}", "usuario",
                  status='falha')
        return False, "Não é permitido remover usuários padrão do sistema"
    
    try:
        conn = connect()
        c = conn.cursor()
        
        c.execute('DELETE FROM usuarios WHERE username = ?', (username,))
        
        if c.rowcount == 0:
            conn.close()
            log_action(deleted_by, f"Tentativa de remover usuário inexistente: {username}", "usuario",
                      status='falha')
            return False, "Usuário não encontrado"
        
        conn.commit()
        conn.close()
        
        # Log de remoção de usuário
        log_action(deleted_by, f"Removeu usuário: {username}", "usuario")
        
        return True, "Usuário removido com sucesso"
        
    except sqlite3.Error as e:
        print(f"Erro ao remover usuário: {e}")
        log_action(deleted_by, f"Erro ao remover usuário {username}: {str(e)}", "usuario",
                  status='falha')
        return False, f"Erro no banco de dados: {str(e)}"

# --- Funções de validação ---
def employee_exists(emp_id):
    """Verifica se um funcionário existe no banco (forma eficiente)"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('SELECT 1 FROM funcionarios WHERE id=?', (emp_id,))
        exists = c.fetchone() is not None
        conn.close()
        return exists
    except sqlite3.Error as e:
        print(f"Erro ao verificar funcionário: {e}")
        return False

# --- Funções de acesso ---
def add_employee_db(name, created_by='system'):
    """Adiciona um funcionário ao banco"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('INSERT INTO funcionarios (name) VALUES (?)', (name,))
        emp_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Log de adição de funcionário
        log_action(created_by, f"Adicionou funcionário: {name} (ID: {emp_id})", "funcionario",
                  detalhes=f"ID: {emp_id}, Nome: {name}")
        
        return emp_id
    except sqlite3.Error as e:
        print(f"Erro ao adicionar funcionário: {e}")
        log_action(created_by, f"Erro ao adicionar funcionário {name}: {str(e)}", "funcionario",
                  status='falha')
        return None

def remove_employee_db(emp_id, deleted_by='system'):
    """Remove um funcionário e todos os seus registros relacionados"""
    try:
        conn = connect()
        c = conn.cursor()
        
        # Buscar nome do funcionário antes de remover
        c.execute('SELECT name FROM funcionarios WHERE id=?', (emp_id,))
        result = c.fetchone()
        emp_name = result[0] if result else 'Desconhecido'
        
        c.execute('DELETE FROM eventos WHERE funcionario_id=?', (emp_id,))
        eventos_removidos = c.rowcount
        
        c.execute('DELETE FROM folgas WHERE funcionario_id=?', (emp_id,))
        folgas_removidas = c.rowcount
        
        c.execute('DELETE FROM funcionarios WHERE id=?', (emp_id,))
        
        conn.commit()
        conn.close()
        
        # Log de remoção de funcionário
        log_action(deleted_by, f"Removeu funcionário: {emp_name} (ID: {emp_id})", "funcionario",
                  detalhes=f"Eventos removidos: {eventos_removidos}, Folgas removidas: {folgas_removidas}")
        
        return True
    except sqlite3.Error as e:
        print(f"Erro ao remover funcionário: {e}")
        log_action(deleted_by, f"Erro ao remover funcionário ID {emp_id}: {str(e)}", "funcionario",
                  status='falha')
        return False

def list_employees_db():
    """Lista todos os funcionários cadastrados"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('SELECT id, name FROM funcionarios ORDER BY name')
        result = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
        conn.close()
        return result
    except sqlite3.Error as e:
        print(f"Erro ao listar funcionários: {e}")
        return []

def record_event_db(emp_id, event_type, timestamp=None, recorded_by='system'):
    """Registra um evento de ponto para um funcionário"""
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    ts_str = timestamp.isoformat()
    date_str = timestamp.date().isoformat()
    
    try:
        conn = connect()
        c = conn.cursor()
        
        # Buscar nome do funcionário
        c.execute('SELECT name FROM funcionarios WHERE id=?', (emp_id,))
        result = c.fetchone()
        emp_name = result[0] if result else 'Desconhecido'
        
        # Verificar duplicidade
        c.execute(
            'SELECT id FROM eventos WHERE funcionario_id=? AND tipo=? AND DATE(timestamp)=?', 
            (emp_id, event_type, date_str)
        )
        
        if c.fetchone():
            conn.close()
            log_action(recorded_by, f"Tentativa de evento duplicado - {emp_name}: {event_type}", "evento",
                      detalhes=f"Funcionário: {emp_name} (ID: {emp_id}), Tipo: {event_type}, Data: {date_str}",
                      status='falha')
            return False, 'Evento já registrado para este dia'
        
        # Inserir evento
        c.execute(
            'INSERT INTO eventos (funcionario_id, tipo, timestamp) VALUES (?,?,?)',
            (emp_id, event_type, ts_str)
        )
        conn.commit()
        conn.close()
        
        # Log de registro de evento
        log_action(recorded_by, f"Registrou {event_type} - {emp_name}", "evento",
                  detalhes=f"Funcionário: {emp_name} (ID: {emp_id}), Tipo: {event_type}, Timestamp: {ts_str}")
        
        return True, 'Evento registrado com sucesso'
        
    except sqlite3.Error as e:
        log_action(recorded_by, f"Erro ao registrar evento: {str(e)}", "evento",
                  status='falha')
        return False, f'Erro no banco de dados: {str(e)}'

def add_holiday_db(date_obj, added_by='system'):
    """Adiciona um feriado ao banco"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO feriados (data) VALUES (?)', (date_obj.isoformat(),))
        
        if c.rowcount > 0:
            # Log apenas se realmente adicionou
            log_action(added_by, f"Adicionou feriado: {date_obj.strftime('%d/%m/%Y')}", "feriado",
                      detalhes=f"Data: {date_obj.isoformat()}")
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao adicionar feriado: {e}")
        log_action(added_by, f"Erro ao adicionar feriado {date_obj}: {str(e)}", "feriado",
                  status='falha')
        return False

def set_day_off_db(emp_id, date_obj, set_by='system'):
    """Marca uma folga para um funcionário"""
    try:
        conn = connect()
        c = conn.cursor()
        
        # Buscar nome do funcionário
        c.execute('SELECT name FROM funcionarios WHERE id=?', (emp_id,))
        result = c.fetchone()
        emp_name = result[0] if result else 'Desconhecido'
        
        c.execute(
            'INSERT OR REPLACE INTO folgas (funcionario_id, data) VALUES (?,?)',
            (emp_id, date_obj.isoformat())
        )
        
        conn.commit()
        conn.close()
        
        # Log de folga
        log_action(set_by, f"Marcou folga para {emp_name}", "folga",
                  detalhes=f"Funcionário: {emp_name} (ID: {emp_id}), Data: {date_obj.strftime('%d/%m/%Y')}")
        
        return True
    except sqlite3.Error as e:
        print(f"Erro ao adicionar folga: {e}")
        log_action(set_by, f"Erro ao marcar folga: {str(e)}", "folga",
                  status='falha')
        return False

def get_events_by_month(emp_id, year, month):
    """Retorna todos os eventos de um funcionário em um mês específico"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('''
            SELECT tipo, timestamp FROM eventos 
            WHERE funcionario_id=? 
            AND strftime('%Y', timestamp)=? 
            AND strftime('%m', timestamp)=?
            ORDER BY timestamp
        ''', (emp_id, str(year), f'{month:02d}'))
        events = c.fetchall()
        conn.close()
        return events
    except sqlite3.Error as e:
        print(f"Erro ao buscar eventos: {e}")
        return []

def get_all_holidays():
    """Retorna todos os feriados cadastrados"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('SELECT data FROM feriados')
        holidays = [datetime.date.fromisoformat(row[0]) for row in c.fetchall()]
        conn.close()
        return holidays
    except sqlite3.Error as e:
        print(f"Erro ao buscar feriados: {e}")
        return []

def get_employee_days_off(emp_id):
    """Retorna todas as folgas de um funcionário"""
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('SELECT data FROM folgas WHERE funcionario_id=?', (emp_id,))
        days_off = [datetime.date.fromisoformat(row[0]) for row in c.fetchall()]
        conn.close()
        return days_off
    except sqlite3.Error as e:
        print(f"Erro ao buscar folgas: {e}")
        return []

def adjust_event_db(emp_id, event_type, timestamp, justificativa, adjusted_by='admin'):
    """
    Adiciona ou ajusta um evento de ponto com justificativa obrigatória
    """
    if not justificativa or not justificativa.strip():
        log_action(adjusted_by, f"Tentativa de ajuste sem justificativa - {emp_id}:{event_type}", 
                  "evento", status='falha')
        return False, "Justificativa é obrigatória", None
    
    ts_str = timestamp.isoformat()
    date_str = timestamp.date().isoformat()
    
    try:
        conn = connect()
        c = conn.cursor()
        
        c.execute('SELECT name FROM funcionarios WHERE id=?', (emp_id,))
        result = c.fetchone()
        emp_name = result[0] if result else 'Desconhecido'
        
        c.execute(
            'SELECT id FROM eventos WHERE funcionario_id=? AND tipo=? AND DATE(timestamp)=?',
            (emp_id, event_type, date_str)
        )
        existing = c.fetchone()
        
        if existing:
            event_id = existing[0]
            c.execute('UPDATE eventos SET timestamp=? WHERE id=?', (ts_str, event_id))
            action = f"Ajustou {event_type} para {timestamp.strftime('%H:%M')} - {emp_name}"
        else:
            c.execute(
                'INSERT INTO eventos (funcionario_id, tipo, timestamp) VALUES (?,?,?)',
                (emp_id, event_type, ts_str)
            )
            event_id = c.lastrowid
            action = f"Adicionou {event_type} às {timestamp.strftime('%H:%M')} - {emp_name}"
        
        conn.commit()
        conn.close()
        
        log_action(adjusted_by, action, "evento",
                  detalhes=f"Funcionário: {emp_name} (ID: {emp_id}), Tipo: {event_type}, "
                          f"Hora: {timestamp.strftime('%H:%M')}, Justificativa: {justificativa}")
        
        return True, "Evento ajustado com sucesso", event_id
        
    except sqlite3.Error as e:
        log_action(adjusted_by, f"Erro ao ajustar evento: {str(e)}", "evento", status='falha')
        return False, f"Erro no banco de dados: {str(e)}", None


def remove_event_db(event_id, emp_id, justificativa, removed_by='admin'):
    """
    Remove um evento de ponto com justificativa obrigatória
    """
    if not justificativa or not justificativa.strip():
        log_action(removed_by, f"Tentativa de remover evento sem justificativa - ID:{event_id}", 
                  "evento", status='falha')
        return False, "Justificativa é obrigatória"
    
    try:
        conn = connect()
        c = conn.cursor()
        
        c.execute('SELECT funcionario_id, tipo, timestamp FROM eventos WHERE id=?', (event_id,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            log_action(removed_by, f"Tentativa de remover evento inexistente - ID:{event_id}", 
                      "evento", status='falha')
            return False, "Evento não encontrado"
        
        func_id, event_type, ts_str = result
        
        if func_id != emp_id:
            conn.close()
            log_action(removed_by, f"Tentativa de remover evento de outro funcionário - ID:{event_id}", 
                      "evento", status='falha')
            return False, "Funcionário não corresponde"
        
        c.execute('SELECT name FROM funcionarios WHERE id=?', (emp_id,))
        emp_result = c.fetchone()
        emp_name = emp_result[0] if emp_result else 'Desconhecido'
        
        c.execute('DELETE FROM eventos WHERE id=?', (event_id,))
        conn.commit()
        conn.close()
        
        ts_dt = datetime.datetime.fromisoformat(ts_str)
        log_action(removed_by, f"Removeu {event_type} - {emp_name}", "evento",
                  detalhes=f"Funcionário: {emp_name} (ID: {emp_id}), Tipo: {event_type}, "
                          f"Horário original: {ts_dt.strftime('%H:%M')}, "
                          f"Justificativa: {justificativa}")
        
        return True, "Evento removido com sucesso"
        
    except sqlite3.Error as e:
        log_action(removed_by, f"Erro ao remover evento: {str(e)}", "evento", status='falha')
        return False, f"Erro no banco de dados: {str(e)}"


def get_employee_events_by_date(emp_id, date_obj):
    """
    Retorna todos os eventos de um funcionário em uma data específica
    """
    try:
        conn = connect()
        c = conn.cursor()
        date_str = date_obj.isoformat()
        
        c.execute('''
            SELECT id, tipo, timestamp FROM eventos
            WHERE funcionario_id=? AND DATE(timestamp)=?
            ORDER BY timestamp
        ''', (emp_id, date_str))
        
        events = []
        for row in c.fetchall():
            events.append({
                'id': row[0],
                'tipo': row[1],
                'timestamp': datetime.datetime.fromisoformat(row[2])
            })
        
        conn.close()
        return events
    except sqlite3.Error as e:
        print(f"Erro ao buscar eventos: {e}")
        return []
