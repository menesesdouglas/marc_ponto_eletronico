import datetime
import calendar
from db import (
    add_employee_db, remove_employee_db, list_employees_db, 
    record_event_db, add_holiday_db, set_day_off_db,
    employee_exists, get_events_by_month, get_all_holidays,
    get_employee_days_off
)

EVENT_TYPES = ['entrada', 'inicio_descanso', 'fim_descanso', 'saida']

# Variável global para armazenar o usuário atual
_current_user = 'system'

def set_current_user(username):
    """Define o usuário atual para logs de auditoria"""
    global _current_user
    _current_user = username

def get_current_user():
    """Retorna o usuário atual"""
    return _current_user

# --- Funções de funcionário ---
def add_employee(name):
    """Cadastra funcionário no banco e retorna o ID"""
    if not name or not name.strip():
        return None, 'Nome não pode estar vazio'
    
    emp_id = add_employee_db(name.strip(), created_by=get_current_user())
    if emp_id:
        return emp_id, 'Funcionário cadastrado com sucesso'
    return None, 'Erro ao cadastrar funcionário'

def remove_employee(emp_id):
    """Remove funcionário e todos os registros relacionados"""
    if not employee_exists(emp_id):
        return False, 'Funcionário não encontrado'
    
    success = remove_employee_db(emp_id, deleted_by=get_current_user())
    if success:
        return True, 'Funcionário removido com sucesso'
    return False, 'Erro ao remover funcionário'

def list_employees():
    """Retorna lista de funcionários"""
    return list_employees_db()

def get_employee_by_id(emp_id):
    """Retorna os dados de um funcionário específico"""
    employees = list_employees_db()
    for emp in employees:
        if emp['id'] == emp_id:
            return emp
    return None

# --- Funções de eventos ---
def validate_event_sequence(emp_id, event_type, date_obj):
    """
    Valida se a sequência de eventos está correta
    Ordem esperada: entrada -> inicio_descanso -> fim_descanso -> saida
    """
    from db import connect
    import sqlite3
    
    try:
        conn = connect()
        c = conn.cursor()
        c.execute('''
            SELECT tipo FROM eventos 
            WHERE funcionario_id=? AND DATE(timestamp)=?
            ORDER BY timestamp
        ''', (emp_id, date_obj.isoformat()))
        
        existing_events = [row[0] for row in c.fetchall()]
        conn.close()
        
        # Regras de validação
        if event_type == 'entrada':
            if 'entrada' in existing_events:
                return False, 'Entrada já registrada hoje'
                
        elif event_type == 'inicio_descanso':
            if 'entrada' not in existing_events:
                return False, 'Registre a entrada primeiro'
            if 'inicio_descanso' in existing_events:
                return False, 'Início de descanso já registrado'
                
        elif event_type == 'fim_descanso':
            if 'inicio_descanso' not in existing_events:
                return False, 'Registre o início do descanso primeiro'
            if 'fim_descanso' in existing_events:
                return False, 'Fim de descanso já registrado'
                
        elif event_type == 'saida':
            if 'entrada' not in existing_events:
                return False, 'Registre a entrada primeiro'
            if 'saida' in existing_events:
                return False, 'Saída já registrada hoje'
            # Verificar se tem descanso aberto
            if 'inicio_descanso' in existing_events and 'fim_descanso' not in existing_events:
                return False, 'Finalize o descanso antes de registrar a saída'
        
        return True, 'OK'
        
    except sqlite3.Error as e:
        return False, f'Erro ao validar sequência: {str(e)}'

def record_event(emp_id, event_type, timestamp=None):
    """Registra evento de ponto para funcionário com validação"""
    # Validar funcionário
    if not employee_exists(emp_id):
        return False, 'Funcionário não encontrado'
    
    # Validar tipo de evento
    if event_type not in EVENT_TYPES:
        return False, 'Tipo de evento inválido'
    
    # Definir timestamp
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    # Validar sequência de eventos
    valid, msg = validate_event_sequence(emp_id, event_type, timestamp.date())
    if not valid:
        return False, msg
    
    # Registrar evento
    return record_event_db(emp_id, event_type, timestamp, recorded_by=get_current_user())

def set_day_off(emp_id, date_obj):
    """Marca folga para funcionário"""
    if not employee_exists(emp_id):
        return False, 'Funcionário não encontrado'
    
    success = set_day_off_db(emp_id, date_obj, set_by=get_current_user())
    if success:
        return True, 'Folga registrada com sucesso'
    return False, 'Erro ao registrar folga'

# --- Feriados ---
def add_holiday(date_obj):
    """Adiciona feriado no banco"""
    success = add_holiday_db(date_obj, added_by=get_current_user())
    if success:
        return True, 'Feriado adicionado com sucesso'
    return False, 'Erro ao adicionar feriado'

# --- Consulta de folhas ---
def get_timesheet(emp_id, year, month):
    """Retorna eventos, feriados e folgas do mês para funcionário"""
    # Validar se funcionário existe
    if not employee_exists(emp_id):
        return []
    
    # Buscar dados
    events_raw = get_events_by_month(emp_id, year, month)
    holidays_raw = get_all_holidays()
    folgas_raw = get_employee_days_off(emp_id)
    
    # Montar estrutura por dia
    _, ndays = calendar.monthrange(year, month)
    days = []
    
    for d in range(1, ndays + 1):
        dt = datetime.date(year, month, d)
        
        # Filtrar eventos do dia
        day_events = [
            {
                'type': e[0], 
                'ts': datetime.datetime.fromisoformat(e[1])
            } 
            for e in events_raw 
            if datetime.date.fromisoformat(e[1][:10]) == dt
        ]
        
        day = {
            'date': dt,
            'events': day_events,
            'holiday': dt in holidays_raw,
            'off': dt in folgas_raw
        }
        days.append(day)
    
    return days

# --- Cálculo de duração do dia ---
def compute_work_duration(day):
    """
    Calcula a duração trabalhada no dia
    Fórmula: (saída - entrada) - total_de_descansos
    """
    events = day['events']
    
    # Buscar entrada e saída
    entry = next((e['ts'] for e in events if e['type'] == 'entrada'), None)
    exit_ = next((e['ts'] for e in reversed(events) if e['type'] == 'saida'), None)
    
    # Validações
    if not entry:
        return None  # Sem entrada
    if not exit_:
        return None  # Sem saída
    if exit_ <= entry:
        return None  # Saída antes da entrada (erro)
    
    # Calcular períodos de descanso
    starts = [e['ts'] for e in events if e['type'] == 'inicio_descanso']
    ends = [e['ts'] for e in events if e['type'] == 'fim_descanso']
    
    total_break = datetime.timedelta()
    
    for i in range(min(len(starts), len(ends))):
        s, e = starts[i], ends[i]
        if e > s:
            total_break += (e - s)
    
    # Calcular tempo trabalhado
    work = exit_ - entry - total_break
    
    if work.total_seconds() < 0:
        return None  # Resultado inválido
    
    return work

def format_timedelta(td):
    """Formata timedelta em formato legível (Xh YYm)"""
    if td is None:
        return None
    
    seconds = int(td.total_seconds())
    h = seconds // 3600
    m = (seconds % 3600) // 60
    
    return f'{h}h{m:02d}m'

def get_monthly_summary(emp_id, year, month):
    """Retorna resumo mensal: total de horas, dias trabalhados, etc."""
    days = get_timesheet(emp_id, year, month)
    
    total_hours = datetime.timedelta()
    worked_days = 0
    holidays = 0
    days_off = 0
    
    for day in days:
        if day['holiday']:
            holidays += 1
            continue
        if day['off']:
            days_off += 1
            continue
        
        duration = compute_work_duration(day)
        if duration:
            total_hours += duration
            worked_days += 1
    
    return {
        'total_hours': total_hours,
        'worked_days': worked_days,
        'holidays': holidays,
        'days_off': days_off,
        'total_hours_formatted': format_timedelta(total_hours)
    }

# --- Ajustes Administrativos ---
def adjust_event(emp_id, event_type, timestamp, justificativa):
    """
    Ajusta (insere ou edita) um evento de ponto com justificativa
    """
    from db import adjust_event_db
    
    if not employee_exists(emp_id):
        return False, "Funcionário não encontrado"
    
    if event_type not in EVENT_TYPES:
        return False, "Tipo de evento inválido"
    
    if not justificativa or not justificativa.strip():
        return False, "Justificativa é obrigatória"
    
    if len(justificativa.strip()) < 10:
        return False, "Justificativa deve ter no mínimo 10 caracteres"
    
    success, msg, event_id = adjust_event_db(emp_id, event_type, timestamp, 
                                             justificativa.strip(), 
                                             adjusted_by=get_current_user())
    
    return success, msg


def remove_event(event_id, emp_id, justificativa):
    """
    Remove um evento de ponto com justificativa obrigatória
    """
    from db import remove_event_db
    
    if not employee_exists(emp_id):
        return False, "Funcionário não encontrado"
    
    if not justificativa or not justificativa.strip():
        return False, "Justificativa é obrigatória"
    
    if len(justificativa.strip()) < 10:
        return False, "Justificativa deve ter no mínimo 10 caracteres"
    
    success, msg = remove_event_db(event_id, emp_id, justificativa.strip(), 
                                    removed_by=get_current_user())
    
    return success, msg


def get_employee_events(emp_id, date_obj):
    """
    Retorna eventos de um funcionário em uma data específica
    """
    from db import get_employee_events_by_date
    
    if not employee_exists(emp_id):
        return []
    
    return get_employee_events_by_date(emp_id, date_obj)
