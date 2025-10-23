"""
Marc - Interface Gráfica
"""

import customtkinter as ctk
from tkinter import messagebox, ttk
from core_db import (
    add_employee, remove_employee, list_employees,
    record_event, get_timesheet, compute_work_duration,
    format_timedelta, add_holiday, set_day_off,
    get_employee_by_id, get_monthly_summary
)
from db import get_logs, get_logs_summary, clear_old_logs, log_action
import datetime
import calendar
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

EVENT_TYPES = ['entrada', 'inicio_descanso', 'fim_descanso', 'saida']

# Paleta de cores Marc
COLORS = {
    'primary': '#2196F3',
    'secondary': '#1976D2',
    'success': '#4CAF50',
    'danger': '#F44336',
    'warning': '#FF9800',
    'background': '#F5F7FA',
    'card': '#FFFFFF',
    'text': '#2C3E50',
    'text_light': '#7F8C8D',
    'accent': '#00BCD4',
    'border': '#E0E0E0'
}

class PontoFlowApp(ctk.CTk):
    def __init__(self, is_admin=False, current_user='system'):
        super().__init__()
        self.is_admin = is_admin
        self.current_user = current_user
        
        # Configurações da janela
        self.title(f"Marc - {'Administrador' if is_admin else 'Funcionário'}")
        self.geometry("1100x700")
        
        # Configurar tema
        ctk.set_appearance_mode("light")
        
        # Container principal
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS['background'])
        self.main_container.pack(fill="both", expand=True)
        
        # Header
        self.create_header()
        
        # Criar abas
        self.tabview = ctk.CTkTabview(
            self.main_container,
            width=1080,
            height=600,
            fg_color=COLORS['card'],
            segmented_button_fg_color=COLORS['primary'],
            segmented_button_selected_color=COLORS['secondary'],
            segmented_button_selected_hover_color=COLORS['secondary'],
            segmented_button_unselected_color=COLORS['primary'],
            segmented_button_unselected_hover_color=COLORS['accent']
        )
        self.tabview.pack(padx=10, pady=(0, 10))
        
        self.tabview.add("📍 Registro de Ponto")
        self.tabview.add("📊 Folha de Ponto")
        
        if is_admin:
            self.tabview.add("👥 Funcionários")
            self.tabview.add("🏖️ Folgas")
            self.tabview.add("🎉 Feriados")
            self.tabview.add("🔧 Ajuste de Ponto")
            self.tabview.add("📋 Logs de Auditoria")
        
        # Inicializar abas
        self.init_registro_tab()
        self.init_folha_tab()
        
        if is_admin:
            self.init_funcionarios_tab()
            self.init_day_off_tab()
            self.init_feriados_tab()
            self.init_adjust_ponto_tab()
            self.init_logs_tab()
        if is_admin:
            self.tabview.add("💾 Backups")
            self.init_backup_tab()

    def export_logs_pdf(self):
        """Exporta os logs de auditoria exibidos na tabela para PDF com layout profissional e sem corte"""
        logs = self.get_displayed_logs()  # Obtém os logs exibidos atualmente

        if not logs:
            messagebox.showwarning("Aviso", "Nenhum log para exportar.")
            return

        from datetime import datetime
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        filename = f"Logs_Auditoria_{timestamp}.pdf"

        try:
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            # Título
            c.setFillColorRGB(0.13, 0.59, 0.95)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Relatório de Logs de Auditoria")

            # Preparar dados para a tabela
            styleSheet = getSampleStyleSheet()
            data = []

            # Cabeçalho
            headers = ["Data/Hora", "Usuário", "Ação", "Categoria", "Status"]
            data.append([Paragraph(f"<b>{h}</b>", styleSheet['Normal']) for h in headers])

            # Dados
            for log in logs:
                row = [
                    Paragraph(log['timestamp'][:19], styleSheet['Normal']),
                    Paragraph(log['usuario'], styleSheet['Normal']),
                    Paragraph(log['acao'][:100] + ("..." if len(log['acao']) > 100 else ""), styleSheet['Normal']),
                    Paragraph(log['categoria'], styleSheet['Normal']),
                    Paragraph(log['status'], styleSheet['Normal'])
                ]
                data.append(row)

            # Criar tabela
            table = Table(data, colWidths=[1.0*inch, 1.0*inch, 2.5*inch, 1.0*inch, 0.8*inch])

            # Estilo da tabela
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('WORDWRAP', (0, 0), (-1, -1), True),
            ]))

            # Calcular posição dinâmica
            table.wrapOn(c, width - 100, height)  # Calcula o tamanho necessário
            table_height = table._height  # Altura real da tabela

            # Posicionar a tabela abaixo do título, com margem
            y_position = height - 80 - table_height  # Começa abaixo do título

            # Se a tabela for muito grande, quebra em páginas
            if y_position < 50:
                c.showPage()
                y_position = height - 50

            # Desenhar a tabela
            table.drawOn(c, 50, y_position)

            # Salvar
            c.showPage()
            c.save()

            messagebox.showinfo("✓ Sucesso", f"Relatório salvo como:\n{filename}")

        except Exception as e:
            messagebox.showerror("✗ Erro", f"Erro ao salvar PDF:\n{str(e)}")

    def get_displayed_logs(self):
        """Retorna os logs atualmente exibidos na Treeview de logs"""
        logs = []
        for child in self.logs_tree.get_children():
            item = self.logs_tree.item(child)
            values = item['values']
            logs.append({
                'timestamp': values[0],
                'usuario': values[1],
                'acao': values[2],
                'categoria': values[3],
                'status': values[4]
            })
        return logs
        
    def init_backup_tab(self):
        """Inicializa a aba de gerenciamento de backups"""
        from backup import BackupManager
        
        tab = self.tabview.tab("💾 Backups")
        
        # Card de backup manual
        manual_card = self.create_card(tab, "🔄 Backup Manual")
        manual_card.pack(fill="x", pady=10, padx=10)
        
        manual_frame = ctk.CTkFrame(manual_card, fg_color="transparent")
        manual_frame.pack(fill="x", pady=15, padx=20)
        
        ctk.CTkButton(
            manual_frame,
            text="📌 Backup Diário Agora",
            command=self.backup_daily_action,
            width=180,
            height=40,
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary'],
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            manual_frame,
            text="📌 Backup Semanal Agora",
            command=self.backup_weekly_action,
            width=180,
            height=40,
            fg_color=COLORS['success'],
            hover_color='#45A049',
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            manual_frame,
            text="🧹 Limpar Antigos",
            command=self.cleanup_backups_action,
            width=140,
            height=40,
            fg_color=COLORS['warning'],
            hover_color='#F57C00',
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        # Card de informações
        info_card = self.create_card(tab, "ℹ️ Informações de Backups")
        info_card.pack(fill="both", expand=True, pady=10, padx=10)
        
        self.backup_info_textbox = ctk.CTkTextbox(
            info_card,
            font=ctk.CTkFont(family="Courier", size=10),
            fg_color="#F8F9FA",
            text_color=COLORS['text'],
            height=300
        )
        self.backup_info_textbox.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Botão de atualização
        update_frame = ctk.CTkFrame(info_card, fg_color="transparent")
        update_frame.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkButton(
            update_frame,
            text="🔄 Atualizar Informações",
            command=self.refresh_backup_info,
            fg_color=COLORS['accent'],
            hover_color='#0097A7'
        ).pack()
        
        # Card de restauração
        restore_card = self.create_card(tab, "♻️ Restaurar Backup")
        restore_card.pack(fill="x", pady=10, padx=10)
        
        restore_frame = ctk.CTkFrame(restore_card, fg_color="transparent")
        restore_frame.pack(fill="x", pady=15, padx=20)
        
        ctk.CTkLabel(
            restore_frame,
            text="Selecione um backup:",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w")
        
        self.backup_restore_var = ctk.StringVar()
        self.backup_restore_combo = ctk.CTkComboBox(
            restore_frame,
            values=[],
            variable=self.backup_restore_var,
            width=400,
            border_color=COLORS['danger'],
            button_color=COLORS['danger'],
            state="disabled"
        )
        self.backup_restore_combo.pack(fill="x", pady=10)
        
        ctk.CTkButton(
            restore_frame,
            text="⚠️ Restaurar Selecionado",
            command=self.restore_backup_action,
            width=250,
            height=40,
            fg_color=COLORS['danger'],
            hover_color='#D32F2F',
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=10)
        
        # Info
        info_frame = ctk.CTkFrame(restore_card, fg_color=COLORS['background'], corner_radius=10)
        info_frame.pack(fill="x", pady=10, padx=20, side="bottom")
        
        ctk.CTkLabel(
            info_frame,
            text="⚠️ ATENÇÃO: Restaurar um backup substitui o banco de dados atual!\n"
                "Um backup do banco atual será criado antes da restauração.",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['danger'],
            justify="center"
        ).pack(pady=10)
        
        # Carregar informações de backup inicialmente
        self.refresh_backup_info()

    def refresh_backup_info(self):
        """Atualiza as informações de backup na interface"""
        from backup import BackupManager
        
        backup_manager = BackupManager()
        backup_info = backup_manager.get_backup_info()
        
        self.backup_info_textbox.delete("1.0", "end")
        
        # Cabeçalho
        self.backup_info_textbox.insert("end", "=" * 70 + "\n")
        self.backup_info_textbox.insert("end", "INFORMAÇÕES DE BACKUP\n")
        self.backup_info_textbox.insert("end", "=" * 70 + "\n\n")
        
        # Resumo geral
        self.backup_info_textbox.insert("end", "RESUMO GERAL:\n")
        self.backup_info_textbox.insert("end", f"  Total de Backups: {backup_info['total_backups']}\n")
        
        if backup_info['last_backup']:
            self.backup_info_textbox.insert("end", f"  Último Backup: {backup_info['last_backup'][:19]}\n")
        else:
            self.backup_info_textbox.insert("end", "  Último Backup: Nenhum\n")
        
        if backup_info['last_weekly_backup']:
            self.backup_info_textbox.insert("end", f"  Último Backup Semanal: {backup_info['last_weekly_backup'][:19]}\n")
        else:
            self.backup_info_textbox.insert("end", "  Último Backup Semanal: Nenhum\n")
        
        self.backup_info_textbox.insert("end", "\n")
        
        # Lista de backups
        if backup_info['backups']:
            self.backup_info_textbox.insert("end", "BACKUPS DISPONÍVEIS:\n")
            self.backup_info_textbox.insert("end", "-" * 70 + "\n")
            
            # Atualizar combobox de restauração
            backup_filenames = [b['filename'] for b in backup_info['backups']]
            self.backup_restore_combo.configure(values=backup_filenames, state="normal")
            if backup_filenames:
                self.backup_restore_combo.set(backup_filenames[0])
            
            for i, backup in enumerate(backup_info['backups'], 1):
                self.backup_info_textbox.insert("end", 
                    f"\n{i}. {backup['filename']}\n"
                    f"   Tipo: {backup['type'].upper()}\n"
                    f"   Data: {backup['timestamp'][:19]}\n"
                    f"   Tamanho: {backup['size_mb']} MB\n"
                )
        else:
            self.backup_info_textbox.insert("end", "Nenhum backup disponível ainda.\n")
            self.backup_restore_combo.configure(state="disabled")
        
        self.backup_info_textbox.insert("end", "\n" + "=" * 70 + "\n")

    def backup_daily_action(self):
        """Executa um backup diário manual"""
        from backup import BackupManager
        from db import log_action
        from core_db import get_current_user
        
        backup_manager = BackupManager()
        success, backup_path, msg = backup_manager.create_backup('daily')
        
        if success:
            log_action(get_current_user(), "Executou backup diário manual", "backup",
                    detalhes=f"Arquivo: {backup_path}")
            messagebox.showinfo("✓ Sucesso", msg)
            self.refresh_backup_info()
        else:
            log_action(get_current_user(), "Falha ao executar backup diário manual", "backup",
                    detalhes=msg, status='falha')
            messagebox.showerror("✗ Erro", msg)

    def backup_weekly_action(self):
        """Executa um backup semanal manual"""
        from backup import BackupManager
        from db import log_action
        from core_db import get_current_user
        
        backup_manager = BackupManager()
        success, backup_path, msg = backup_manager.create_backup('weekly')
        
        if success:
            log_action(get_current_user(), "Executou backup semanal manual", "backup",
                    detalhes=f"Arquivo: {backup_path}")
            messagebox.showinfo("✓ Sucesso", msg)
            self.refresh_backup_info()
        else:
            log_action(get_current_user(), "Falha ao executar backup semanal manual", "backup",
                    detalhes=msg, status='falha')
            messagebox.showerror("✗ Erro", msg)

    def cleanup_backups_action(self):
        """Limpa backups antigos"""
        from backup import BackupManager
        from db import log_action
        from core_db import get_current_user
        
        confirm = messagebox.askyesno(
            "⚠️ Confirmar Limpeza",
            "Deseja realmente remover backups antigos?\n\n"
            "Serão mantidos:\n"
            "- Últimos 14 backups diários\n"
            "- Últimos 12 backups semanais\n\n"
            "Esta ação não pode ser desfeita!"
        )
        
        if not confirm:
            return
        
        backup_manager = BackupManager()
        removed = backup_manager.cleanup_old_backups(keep_daily=14, keep_weekly=12)
        
        log_action(get_current_user(), "Executou limpeza de backups antigos", "backup",
                detalhes=f"Backups removidos: {removed}")
        
        if removed > 0:
            messagebox.showinfo("✓ Limpeza Concluída", 
                            f"{removed} backup(s) antigo(s) removido(s) com sucesso!")
        else:
            messagebox.showinfo("ℹ️ Limpeza", "Nenhum backup antigo encontrado para remover.")
        
        self.refresh_backup_info()

    def restore_backup_action(self):
        """Restaura um backup selecionado"""
        from backup import BackupManager
        from db import log_action
        from core_db import get_current_user
        
        backup_filename = self.backup_restore_var.get()
        
        if not backup_filename:
            messagebox.showerror("Erro", "Selecione um backup para restaurar")
            return
        
        confirm = messagebox.askyesno(
            "⚠️ ATENÇÃO - Restaurar Backup",
            f"Deseja realmente restaurar o backup:\n\n{backup_filename}\n\n"
            "⚠️ IMPORTANTE:\n"
            "- O banco de dados atual será sobrescrito\n"
            "- Um backup do banco atual será criado automaticamente\n"
            "- Esta ação não pode ser desfeita completamente\n\n"
            "Confirmar?"
        )
        
        if not confirm:
            return
        
        backup_manager = BackupManager()
        success, msg = backup_manager.restore_backup(backup_filename)
        
        if success:
            log_action(get_current_user(), "Restaurou backup do banco de dados", "backup",
                    detalhes=f"Arquivo restaurado: {backup_filename}")
            messagebox.showinfo("✓ Sucesso", msg + "\n\nA aplicação será reiniciada.")
            # Reiniciar aplicação
            import os
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            log_action(get_current_user(), "Falha ao restaurar backup", "backup",
                    detalhes=f"Arquivo: {backup_filename}, Erro: {msg}", status='falha')
            messagebox.showerror("✗ Erro", msg)

    def init_adjust_ponto_tab(self):
        """Inicializa a aba de ajuste administrativo de ponto"""
        tab = self.tabview.tab("🔧 Ajuste de Ponto")
        
        # ===== CARD 1: Adicionar/Editar Evento =====
        add_card = self.create_card(tab, "➕ Adicionar/Editar Evento")
        add_card.pack(fill="x", pady=10, padx=10)
        
        add_frame = ctk.CTkFrame(add_card, fg_color="transparent")
        add_frame.pack(fill="x", pady=15, padx=20)
        
        # Funcionário
        ctk.CTkLabel(add_frame, text="Funcionário:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=5)
        self.adjust_emp_var = ctk.StringVar()
        self.adjust_emp_combo = ctk.CTkComboBox(
            add_frame,
            values=[],
            variable=self.adjust_emp_var,
            width=200,
            border_color=COLORS['primary'],
            button_color=COLORS['primary']
        )
        self.adjust_emp_combo.pack(side="left", padx=5)
        
        # Data
        ctk.CTkLabel(add_frame, text="Data (AAAA-MM-DD):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(20, 5))
        self.adjust_date_var = ctk.StringVar(value=datetime.date.today().isoformat())
        self.adjust_date_entry = ctk.CTkEntry(
            add_frame,
            width=120,
            textvariable=self.adjust_date_var,
            border_color=COLORS['primary']
        )
        self.adjust_date_entry.pack(side="left", padx=5)
        
        # Botão para carregar eventos
        ctk.CTkButton(
            add_frame,
            text="🔍 Carregar",
            command=self.load_daily_events,
            width=100,
            fg_color=COLORS['accent'],
            hover_color='#0097A7'
        ).pack(side="left", padx=10)
        
        # === Seleção de tipo de evento ===
        type_frame = ctk.CTkFrame(add_card, fg_color="transparent")
        type_frame.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkLabel(type_frame, text="Tipo de Evento:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        self.adjust_type_var = ctk.StringVar(value='entrada')
        
        type_sub_frame = ctk.CTkFrame(type_frame, fg_color="transparent")
        type_sub_frame.pack(anchor="w", pady=5)
        
        event_labels = {
            'entrada': '🟢 Entrada',
            'inicio_descanso': '🟡 Início Descanso',
            'fim_descanso': '🟠 Fim Descanso',
            'saida': '🔴 Saída'
        }
        
        for e in EVENT_TYPES:
            ctk.CTkRadioButton(
                type_sub_frame,
                text=event_labels[e],
                variable=self.adjust_type_var,
                value=e,
                font=ctk.CTkFont(size=10),
                text_color=COLORS['text']
            ).pack(anchor="w", pady=2, padx=20)
        
        # === Hora do evento ===
        hour_frame = ctk.CTkFrame(add_card, fg_color="transparent")
        hour_frame.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkLabel(hour_frame, text="Hora (HH:MM):", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.adjust_time_var = ctk.StringVar(value="09:00")
        self.adjust_time_entry = ctk.CTkEntry(
            hour_frame,
            width=100,
            textvariable=self.adjust_time_var,
            border_color=COLORS['primary'],
            placeholder_text="HH:MM"
        )
        self.adjust_time_entry.pack(anchor="w", pady=5, padx=20)
        
        # === Justificativa ===
        ctk.CTkLabel(add_card, text="Justificativa (obrigatória, mín. 10 caracteres):", 
                    font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS['danger']).pack(anchor="w", pady=(15, 5), padx=20)
        
        self.adjust_justif_text = ctk.CTkTextbox(
            add_card,
            height=80,
            border_color=COLORS['danger'],
            border_width=2
        )
        self.adjust_justif_text.pack(fill="both", padx=20, pady=5)
        
        # Botão
        ctk.CTkButton(
            add_card,
            text="✓ Adicionar/Editar Evento",
            command=self.do_adjust_event,
            width=250,
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['success'],
            hover_color='#45A049'
        ).pack(pady=15)
        
        # ===== CARD 2: Eventos do Dia =====
        events_card = self.create_card(tab, "📅 Eventos do Dia")
        events_card.pack(fill="both", expand=True, pady=10, padx=10)
        
        # Treeview para eventos
        tree_frame = ctk.CTkFrame(events_card, fg_color=COLORS['card'])
        tree_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        columns = ["ID", "Tipo", "Hora", "Ação"]
        self.adjust_events_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.adjust_events_tree.heading(col, text=col)
            if col == "ID":
                self.adjust_events_tree.column(col, width=40, anchor="center")
            elif col == "Tipo":
                self.adjust_events_tree.column(col, width=150, anchor="center")
            elif col == "Hora":
                self.adjust_events_tree.column(col, width=100, anchor="center")
            else:
                self.adjust_events_tree.column(col, width=180, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.adjust_events_tree.yview)
        self.adjust_events_tree.configure(yscrollcommand=scrollbar.set)
        
        self.adjust_events_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                       background="white",
                       foreground=COLORS['text'],
                       rowheight=28,
                       fieldbackground="white",
                       font=('Arial', 10))
        style.configure("Treeview.Heading",
                       background=COLORS['primary'],
                       foreground="white",
                       font=('Arial', 10, 'bold'))
        
        # Bind para clique duplo
        self.adjust_events_tree.bind("<Double-1>", self.on_event_double_click)
        
        self.refresh_employee_comboboxes()

    def load_daily_events(self):
        """Carrega eventos do dia selecionado"""
        emp_str = self.adjust_emp_var.get()
        date_str = self.adjust_date_var.get()
        
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
            date_obj = datetime.date.fromisoformat(date_str)
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Data inválida. Use AAAA-MM-DD")
            return
        
        from core_db import get_employee_events
        events = get_employee_events(emp_id, date_obj)
        
        self.adjust_events_tree.delete(*self.adjust_events_tree.get_children())
        
        if not events:
            messagebox.showinfo("ℹ️ Info", "Nenhum evento encontrado nesta data")
            return
        
        for event in events:
            ts_formatted = event['timestamp'].strftime('%H:%M')
            self.adjust_events_tree.insert("", "end", values=[
                event['id'],
                event['tipo'].replace('_', ' ').upper(),
                ts_formatted,
                "🗑️ Remover"
            ])

    def on_event_double_click(self, event):
        """Manipula clique duplo em um evento"""
        item = self.adjust_events_tree.selection()[0]
        values = self.adjust_events_tree.item(item, 'values')
        
        if values:
            event_id = values[0]
            event_type = values[1].lower().replace(' ', '_')
            event_hour = values[2]
            
            # Preencher formulário
            self.adjust_type_var.set(event_type)
            self.adjust_time_var.set(event_hour)
            
            messagebox.showinfo("ℹ️ Info", "Formulário preenchido com dados do evento.\n"
                                         "Modifique a hora se necessário e clique em Adicionar/Editar")

    def do_adjust_event(self):
        """Executa o ajuste/adição de evento"""
        emp_str = self.adjust_emp_var.get()
        date_str = self.adjust_date_var.get()
        time_str = self.adjust_time_var.get()
        event_type = self.adjust_type_var.get()
        justificativa = self.adjust_justif_text.get("1.0", "end").strip()
        
        # Validações
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        if not justificativa:
            messagebox.showerror("Erro", "Digite a justificativa")
            return
        
        if len(justificativa) < 10:
            messagebox.showerror("Erro", "Justificativa deve ter no mínimo 10 caracteres")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
            date_obj = datetime.date.fromisoformat(date_str)
            h, m = map(int, time_str.split(':'))
            timestamp = datetime.datetime.combine(date_obj, datetime.time(h, m))
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Dados inválidos. Verifique data (AAAA-MM-DD) e hora (HH:MM)")
            return
        
        from core_db import adjust_event
        success, msg = adjust_event(emp_id, event_type, timestamp, justificativa)
        
        if success:
            messagebox.showinfo("✓ Sucesso", msg)
            self.adjust_justif_text.delete("1.0", "end")
            self.adjust_time_var.set("09:00")
            self.load_daily_events()
        else:
            messagebox.showerror("✗ Erro", msg)

    def remove_event_action(self):
        """Remove um evento selecionado"""
        selection = self.adjust_events_tree.selection()
        
        if not selection:
            messagebox.showerror("Erro", "Selecione um evento para remover")
            return
        
        item = selection[0]
        values = self.adjust_events_tree.item(item, 'values')
        event_id = values[0]
        event_type = values[1]
        event_hour = values[2]
        
        emp_str = self.adjust_emp_var.get()
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Dados inválidos")
            return
        
        # Diálogo para justificativa
        justify_window = ctk.CTkToplevel(self)
        justify_window.title("Remover Evento - Justificativa")
        justify_window.geometry("500x300")
        justify_window.resizable(False, False)
        
        ctk.CTkLabel(
            justify_window,
            text=f"Remover: {event_type} às {event_hour}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['danger']
        ).pack(pady=15)
        
        ctk.CTkLabel(
            justify_window,
            text="Justificativa (obrigatória):",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 5))
        
        justif_text = ctk.CTkTextbox(justify_window, height=120, border_color=COLORS['danger'], border_width=2)
        justif_text.pack(fill="both", padx=20, pady=5)
        
        def do_remove():
            justificativa = justif_text.get("1.0", "end").strip()
            
            if not justificativa:
                messagebox.showerror("Erro", "Digite a justificativa")
                return
            
            if len(justificativa) < 10:
                messagebox.showerror("Erro", "Justificativa deve ter no mínimo 10 caracteres")
                return
            
            from core_db import remove_event
            success, msg = remove_event(int(event_id), emp_id, justificativa)
            
            if success:
                messagebox.showinfo("✓ Sucesso", msg)
                justify_window.destroy()
                self.load_daily_events()
            else:
                messagebox.showerror("✗ Erro", msg)
        
        button_frame = ctk.CTkFrame(justify_window, fg_color="transparent")
        button_frame.pack(pady=15)
        
        ctk.CTkButton(
            button_frame,
            text="✓ Remover",
            command=do_remove,
            width=150,
            fg_color=COLORS['danger'],
            hover_color='#D32F2F'
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="✗ Cancelar",
            command=justify_window.destroy,
            width=150,
            fg_color=COLORS['text_light'],
            hover_color='#5F6C7B'
        ).pack(side="left", padx=5)
    
    def create_header(self):
        """Cria o cabeçalho do aplicativo"""
        header = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS['primary'],
            height=70
        )
        header.pack(fill="x", padx=10, pady=10)
        
        # Logo e título
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=15)
        
        ctk.CTkLabel(
            title_frame,
            text="⚡ Marc",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        ).pack(side="left")
        
        # Info do usuário
        user_type = "Administrador" if self.is_admin else "Funcionário"
        ctk.CTkLabel(
            header,
            text=f"👤 {self.current_user} ({user_type})",
            font=ctk.CTkFont(size=12),
            text_color="white"
        ).pack(side="right", padx=20)

    def create_card(self, parent, title=None):
        """Cria um card estilizado"""
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS['card'],
            corner_radius=15,
            border_width=1,
            border_color=COLORS['border']
        )
        
        if title:
            title_label = ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=COLORS['text']
            )
            title_label.pack(pady=(15, 10), padx=20, anchor="w")
        
        return card

    # ============ REGISTRO DE PONTO ============
    def init_registro_tab(self):
        """Inicializa a aba de registro de ponto"""
        tab = self.tabview.tab("📍 Registro de Ponto")
        
        # Card principal
        card = self.create_card(tab, "Registrar Ponto")
        card.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Seleção de funcionário
        ctk.CTkLabel(
            card,
            text="Funcionário:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text']
        ).pack(pady=(20, 5), padx=20, anchor="w")
        
        self.event_emp_var = ctk.StringVar()
        self.event_emp_combobox = ctk.CTkComboBox(
            card,
            values=[],
            variable=self.event_emp_var,
            width=400,
            height=40,
            border_color=COLORS['primary'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['secondary'],
            dropdown_hover_color=COLORS['accent'],
            font=ctk.CTkFont(size=13)
        )
        self.event_emp_combobox.pack(pady=5, padx=20)
        
        # Seleção de tipo de evento
        ctk.CTkLabel(
            card,
            text="Tipo de Evento:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text']
        ).pack(pady=(30, 10), padx=20, anchor="w")
        
        self.event_type_var = ctk.StringVar(value=EVENT_TYPES[0])
        
        events_frame = ctk.CTkFrame(card, fg_color="transparent")
        events_frame.pack(pady=5, padx=20)
        
        event_labels = {
            'entrada': '🟢 Entrada',
            'inicio_descanso': '🟡 Início Descanso',
            'fim_descanso': '🟠 Fim Descanso',
            'saida': '🔴 Saída'
        }
        
        for e in EVENT_TYPES:
            ctk.CTkRadioButton(
                events_frame,
                text=event_labels[e],
                variable=self.event_type_var,
                value=e,
                font=ctk.CTkFont(size=13),
                text_color=COLORS['text'],
                fg_color=COLORS['primary'],
                hover_color=COLORS['accent']
            ).pack(anchor="w", pady=5, padx=30)
        
        # Botão de registro
        ctk.CTkButton(
            card,
            text="✓ Registrar Evento",
            command=self.record_event,
            width=300,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS['success'],
            hover_color='#45A049',
            corner_radius=10
        ).pack(pady=40)
        
        self.refresh_employee_comboboxes()

    def refresh_employee_comboboxes(self):
        """Atualiza os comboboxes de funcionários"""
        employees = list_employees()
        emp_options = [f"{e['id']} - {e['name']}" for e in employees]
        
        if hasattr(self, "event_emp_combobox"):
            self.event_emp_combobox.configure(values=emp_options)
            if emp_options:
                self.event_emp_combobox.set(emp_options[0])
        
        if hasattr(self, "ts_emp_combobox"):
            self.ts_emp_combobox.configure(values=emp_options)
            if emp_options:
                self.ts_emp_combobox.set(emp_options[0])
        
        if hasattr(self, "dayoff_emp_combobox"):
            self.dayoff_emp_combobox.configure(values=emp_options)
            if emp_options:
                self.dayoff_emp_combobox.set(emp_options[0])

    def record_event(self):
        """Registra um evento de ponto"""
        emp_str = self.event_emp_var.get()
        
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
            emp_name = emp_str.split(' - ')[1]
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Funcionário inválido")
            return
        
        event_type = self.event_type_var.get()
        ok, msg = record_event(emp_id, event_type)
        
        if ok:
            messagebox.showinfo("✓ Sucesso", msg)
        else:
            messagebox.showerror("✗ Erro", msg)

    # ============ FOLHA DE PONTO ============
    def init_folha_tab(self):
        """Inicializa a aba de visualização de folha de ponto"""
        tab = self.tabview.tab("📊 Folha de Ponto")
        
        # Card de controles
        control_card = ctk.CTkFrame(tab, fg_color=COLORS['card'], corner_radius=10)
        control_card.pack(fill="x", pady=10, padx=10)
        
        frame_controls = ctk.CTkFrame(control_card, fg_color="transparent")
        frame_controls.pack(fill="x", pady=15, padx=15)
        
        # Funcionário
        ctk.CTkLabel(frame_controls, text="Funcionário:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        self.ts_emp_var = ctk.StringVar()
        self.ts_emp_combobox = ctk.CTkComboBox(
            frame_controls,
            values=[],
            variable=self.ts_emp_var,
            width=250,
            border_color=COLORS['primary'],
            button_color=COLORS['primary']
        )
        self.ts_emp_combobox.pack(side="left", padx=5)
        
        # Mês
        ctk.CTkLabel(frame_controls, text="Mês:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(20, 5))
        self.ts_month_var = ctk.StringVar(value=str(datetime.date.today().month))
        self.ts_month_combobox = ctk.CTkComboBox(
            frame_controls,
            values=[str(i) for i in range(1, 13)],
            variable=self.ts_month_var,
            width=70,
            border_color=COLORS['primary'],
            button_color=COLORS['primary']
        )
        self.ts_month_combobox.pack(side="left", padx=5)
        
        # Ano
        ctk.CTkLabel(frame_controls, text="Ano:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=5)
        self.ts_year_var = ctk.StringVar(value=str(datetime.date.today().year))
        self.ts_year_entry = ctk.CTkEntry(
            frame_controls,
            width=80,
            textvariable=self.ts_year_var,
            border_color=COLORS['primary']
        )
        self.ts_year_entry.pack(side="left", padx=5)
        
        # Botões
        ctk.CTkButton(
            frame_controls,
            text="🔍 Visualizar",
            command=self.view_timesheet,
            width=120,
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary']
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            frame_controls,
            text="📄 Exportar PDF",
            command=self.export_pdf,
            width=140,
            fg_color=COLORS['warning'],
            hover_color='#F57C00'
        ).pack(side="left", padx=5)
        
        # Card de resumo
        self.summary_card = ctk.CTkFrame(tab, fg_color=COLORS['accent'], corner_radius=10)
        self.summary_card.pack(fill="x", pady=5, padx=10)
        
        self.summary_label = ctk.CTkLabel(
            self.summary_card,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="white"
        )
        self.summary_label.pack(pady=10)
        
        # Treeview
        tree_frame = ctk.CTkFrame(tab, fg_color=COLORS['card'])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ["Data", "Entrada", "Início Desc", "Fim Desc", "Saída", "Total", "Status"]
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "Data":
                self.tree.column(col, width=100, anchor="center")
            elif col == "Status":
                self.tree.column(col, width=150, anchor="center")
            else:
                self.tree.column(col, width=90, anchor="center")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Estilo da Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                       background="white",
                       foreground=COLORS['text'],
                       rowheight=28,
                       fieldbackground="white",
                       font=('Arial', 10))
        style.configure("Treeview.Heading",
                       background=COLORS['primary'],
                       foreground="white",
                       font=('Arial', 11, 'bold'))
        style.map('Treeview', background=[('selected', COLORS['accent'])])
        
        self.refresh_employee_comboboxes()

    def view_timesheet(self):
        """Visualiza a folha de ponto"""
        emp_str = self.ts_emp_var.get()
        
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
            month = int(self.ts_month_var.get())
            year = int(self.ts_year_var.get())
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Dados inválidos")
            return
        
        days = get_timesheet(emp_id, year, month)
        summary = get_monthly_summary(emp_id, year, month)
        
        self.summary_label.configure(
            text=f"⏱️ Total: {summary['total_hours_formatted']} | "
                 f"📅 Dias trabalhados: {summary['worked_days']} | "
                 f"🎉 Feriados: {summary['holidays']} | "
                 f"🏖️ Folgas: {summary['days_off']}"
        )
        
        self.tree.delete(*self.tree.get_children())
        
        for day in days:
            flags = []
            bg = "white"
            
            if day['holiday']:
                flags.append("🎉 FERIADO")
                bg = "#FFEBEE"
            if day['off']:
                flags.append("🏖️ FOLGA")
                bg = "#E3F2FD"
            
            flag_str = ", ".join(flags) if flags else "-"
            
            ev_map = {k: '-' for k in EVENT_TYPES}
            for e in day['events']:
                ev_map[e['type']] = e['ts'].strftime('%H:%M')
            
            total = format_timedelta(compute_work_duration(day)) or '-'
            
            item = self.tree.insert("", "end", values=[
                day['date'].strftime('%d/%m/%Y'),
                ev_map['entrada'],
                ev_map['inicio_descanso'],
                ev_map['fim_descanso'],
                ev_map['saida'],
                total,
                flag_str
            ])
            
            if bg != "white":
                self.tree.tag_configure(f'bg_{item}', background=bg)
                self.tree.item(item, tags=(f'bg_{item}',))

    def export_pdf(self):
        """Exporta folha de ponto para PDF"""
        emp_str = self.ts_emp_var.get()
        
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
            month = int(self.ts_month_var.get())
            year = int(self.ts_year_var.get())
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Dados inválidos")
            return
        
        employee = get_employee_by_id(emp_id)
        if not employee:
            messagebox.showerror("Erro", "Funcionário não encontrado")
            return
        
        emp_name = employee['name']
        days = get_timesheet(emp_id, year, month)
        summary = get_monthly_summary(emp_id, year, month)
        
        filename = f"PontoFlow_{emp_name.replace(' ', '_')}_{month:02d}_{year}.pdf"
        
        try:
            c = canvas.Canvas(filename, pagesize=A4)
            
            # Cabeçalho
            c.setFillColorRGB(0.13, 0.59, 0.95)
            c.rect(0, 800, 600, 42, fill=True, stroke=False)
            
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, 815, "⚡ Marc - Folha de Ponto")
            
            y = 770
            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"Funcionário: {emp_name}")
            y -= 20
            c.setFont("Helvetica", 10)
            c.drawString(50, y, f"{calendar.month_name[month]} de {year}")
            y -= 30
            
            # Resumo
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, "Resumo Mensal:")
            y -= 15
            c.setFont("Helvetica", 9)
            c.drawString(50, y, f"Total trabalhado: {summary['total_hours_formatted']}")
            y -= 12
            c.drawString(50, y, f"Dias: {summary['worked_days']} | Feriados: {summary['holidays']} | Folgas: {summary['days_off']}")
            y -= 25
            
            # Tabela
            c.setFont("Helvetica-Bold", 8)
            c.drawString(50, y, "Data")
            c.drawString(110, y, "Entrada")
            c.drawString(170, y, "In.Desc")
            c.drawString(220, y, "Fim Desc")
            c.drawString(280, y, "Saída")
            c.drawString(340, y, "Total")
            c.drawString(400, y, "Status")
            y -= 15
            
            c.setFont("Helvetica", 7)
            
            for day in days:
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 7)
                    y = 800
                
                flags = []
                if day['holiday']:
                    flags.append("FERIADO")
                if day['off']:
                    flags.append("FOLGA")
                flag_str = ", ".join(flags) if flags else "-"
                
                ev_map = {k: '-' for k in EVENT_TYPES}
                for e in day['events']:
                    ev_map[e['type']] = e['ts'].strftime('%H:%M')
                
                total = format_timedelta(compute_work_duration(day)) or '-'
                
                c.drawString(50, y, day['date'].strftime('%d/%m/%Y'))
                c.drawString(110, y, ev_map['entrada'])
                c.drawString(170, y, ev_map['inicio_descanso'])
                c.drawString(220, y, ev_map['fim_descanso'])
                c.drawString(280, y, ev_map['saida'])
                c.drawString(340, y, total)
                c.drawString(400, y, flag_str)
                
                y -= 12
            
            c.save()
            messagebox.showinfo("✓ Sucesso", f"PDF gerado: {filename}")
            
        except Exception as e:
            messagebox.showerror("✗ Erro", f"Erro ao gerar PDF: {str(e)}")

    # ============ FUNCIONÁRIOS (ADMIN) ============
    def init_funcionarios_tab(self):
        """Inicializa a aba de gerenciamento de funcionários"""
        tab = self.tabview.tab("👥 Funcionários")
        
        # Card de adição
        add_card = self.create_card(tab, "➕ Adicionar Funcionário")
        add_card.pack(fill="x", pady=10, padx=10)
        
        add_frame = ctk.CTkFrame(add_card, fg_color="transparent")
        add_frame.pack(fill="x", pady=15, padx=20)
        
        ctk.CTkLabel(
            add_frame,
            text="Nome:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        self.name_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Nome completo do funcionário",
            width=400,
            height=35,
            border_color=COLORS['primary']
        )
        self.name_entry.pack(side="left", padx=5)
        self.name_entry.bind("<Return>", lambda e: self.add_employee())
        
        ctk.CTkButton(
            add_frame,
            text="✓ Adicionar",
            command=self.add_employee,
            width=120,
            height=35,
            fg_color=COLORS['success'],
            hover_color='#45A049'
        ).pack(side="left", padx=5)
        
        # Card de remoção
        remove_card = self.create_card(tab, "🗑️ Remover Funcionário")
        remove_card.pack(fill="x", pady=10, padx=10)
        
        remove_frame = ctk.CTkFrame(remove_card, fg_color="transparent")
        remove_frame.pack(fill="x", pady=15, padx=20)
        
        ctk.CTkLabel(
            remove_frame,
            text="ID:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=5)
        
        self.remove_entry = ctk.CTkEntry(
            remove_frame,
            placeholder_text="ID do funcionário",
            width=150,
            height=35,
            border_color=COLORS['danger']
        )
        self.remove_entry.pack(side="left", padx=5)
        self.remove_entry.bind("<Return>", lambda e: self.remove_employee())
        
        ctk.CTkButton(
            remove_frame,
            text="✗ Remover",
            command=self.remove_employee,
            width=120,
            height=35,
            fg_color=COLORS['danger'],
            hover_color='#D32F2F'
        ).pack(side="left", padx=5)
        
        # Card de lista
        list_card = self.create_card(tab, "📋 Funcionários Cadastrados")
        list_card.pack(fill="both", expand=True, pady=10, padx=10)
        
        self.emp_listbox = ctk.CTkTextbox(
            list_card,
            height=300,
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color="#F8F9FA",
            text_color=COLORS['text']
        )
        self.emp_listbox.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.refresh_employees()

    def refresh_employees(self):
        """Atualiza a lista de funcionários"""
        self.emp_listbox.delete("0.0", "end")
        employees = list_employees()
        
        if not employees:
            self.emp_listbox.insert("end", "📭 Nenhum funcionário cadastrado.\n")
        else:
            self.emp_listbox.insert("end", f"{'ID':<10} {'Nome':<30}\n")
            self.emp_listbox.insert("end", "=" * 50 + "\n")
            for e in employees:
                self.emp_listbox.insert("end", f"{e['id']:<10} {e['name']:<30}\n")
        
        self.refresh_employee_comboboxes()

    def add_employee(self):
        """Adiciona um funcionário"""
        name = self.name_entry.get().strip()
        
        if not name:
            messagebox.showerror("Erro", "Digite o nome do funcionário")
            return
        
        emp_id, msg = add_employee(name)
        
        if emp_id:
            messagebox.showinfo("✓ Sucesso", f"{msg} (ID: {emp_id})")
            self.name_entry.delete(0, "end")
            self.refresh_employees()
        else:
            messagebox.showerror("✗ Erro", msg)

    def remove_employee(self):
        """Remove um funcionário"""
        try:
            emp_id = int(self.remove_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Digite um ID válido")
            return
        
        employee = get_employee_by_id(emp_id)
        if not employee:
            messagebox.showerror("Erro", "Funcionário não encontrado")
            return
        
        confirm = messagebox.askyesno(
            "⚠️ Confirmar Remoção",
            f"Deseja realmente remover '{employee['name']}'?\n\n"
            f"⚠️ Todos os registros de ponto serão deletados!"
        )
        
        if not confirm:
            return
        
        success, msg = remove_employee(emp_id)
        
        if success:
            messagebox.showinfo("✓ Sucesso", msg)
            self.remove_entry.delete(0, "end")
            self.refresh_employees()
        else:
            messagebox.showerror("✗ Erro", msg)

    # ============ FOLGAS (ADMIN) ============
    def init_day_off_tab(self):
        """Inicializa a aba de gerenciamento de folgas"""
        tab = self.tabview.tab("🏖️ Folgas")
        
        card = self.create_card(tab, "Gerenciar Folgas")
        card.pack(pady=30, padx=30, fill="both", expand=True)
        
        # Funcionário
        ctk.CTkLabel(
            card,
            text="Funcionário:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text']
        ).pack(pady=(20, 5), padx=20, anchor="w")
        
        self.dayoff_emp_var = ctk.StringVar()
        self.dayoff_emp_combobox = ctk.CTkComboBox(
            card,
            values=[],
            variable=self.dayoff_emp_var,
            width=400,
            height=40,
            border_color=COLORS['primary'],
            button_color=COLORS['primary']
        )
        self.dayoff_emp_combobox.pack(pady=5, padx=20)
        
        # Data
        ctk.CTkLabel(
            card,
            text="Data da Folga (AAAA-MM-DD):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text']
        ).pack(pady=(30, 5), padx=20, anchor="w")
        
        self.dayoff_date_entry = ctk.CTkEntry(
            card,
            placeholder_text="Ex: 2025-12-25",
            width=400,
            height=40,
            border_color=COLORS['primary']
        )
        self.dayoff_date_entry.pack(pady=5, padx=20)
        self.dayoff_date_entry.bind("<Return>", lambda e: self.add_day_off())
        
        # Botão
        ctk.CTkButton(
            card,
            text="✓ Adicionar Folga",
            command=self.add_day_off,
            width=250,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary']
        ).pack(pady=40)
        
        # Info
        info_frame = ctk.CTkFrame(card, fg_color=COLORS['background'], corner_radius=10)
        info_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            info_frame,
            text="💡 Dica: Use o formato AAAA-MM-DD para as datas\nExemplo: 2025-10-15 para 15 de outubro de 2025",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_light']
        ).pack(pady=15)
        
        self.refresh_employee_comboboxes()

    def add_day_off(self):
        """Adiciona uma folga para um funcionário"""
        date_str = self.dayoff_date_entry.get().strip()
        emp_str = self.dayoff_emp_var.get()
        
        if not emp_str:
            messagebox.showerror("Erro", "Selecione um funcionário")
            return
        
        if not date_str:
            messagebox.showerror("Erro", "Digite uma data")
            return
        
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use AAAA-MM-DD")
            return
        
        try:
            emp_id = int(emp_str.split(' - ')[0])
        except (ValueError, IndexError):
            messagebox.showerror("Erro", "Funcionário inválido")
            return
        
        success, msg = set_day_off(emp_id, date_obj)
        
        if success:
            messagebox.showinfo("✓ Sucesso", msg)
            self.dayoff_date_entry.delete(0, "end")
        else:
            messagebox.showerror("✗ Erro", msg)

    # ============ FERIADOS (ADMIN) ============
    def init_feriados_tab(self):
        """Inicializa a aba de gerenciamento de feriados"""
        tab = self.tabview.tab("🎉 Feriados")
        
        card = self.create_card(tab, "Gerenciar Feriados")
        card.pack(pady=30, padx=30, fill="both", expand=True)
        
        # Data
        ctk.CTkLabel(
            card,
            text="Data do Feriado (AAAA-MM-DD):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text']
        ).pack(pady=(20, 5), padx=20, anchor="w")
        
        self.holiday_date_entry = ctk.CTkEntry(
            card,
            placeholder_text="Ex: 2025-12-25",
            width=400,
            height=40,
            border_color=COLORS['primary']
        )
        self.holiday_date_entry.pack(pady=5, padx=20)
        self.holiday_date_entry.bind("<Return>", lambda e: self.add_holiday())
        
        # Botão
        ctk.CTkButton(
            card,
            text="✓ Adicionar Feriado",
            command=self.add_holiday,
            width=250,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary']
        ).pack(pady=40)
        
        # Info
        info_frame = ctk.CTkFrame(card, fg_color=COLORS['background'], corner_radius=10)
        info_frame.pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Feriados são aplicados para TODOS os funcionários\n💡 Formato: AAAA-MM-DD\n📅 Exemplo: 2025-01-01 para Ano Novo",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_light'],
            justify="left"
        ).pack(pady=15)

    def add_holiday(self):
        """Adiciona um feriado"""
        date_str = self.holiday_date_entry.get().strip()
        
        if not date_str:
            messagebox.showerror("Erro", "Digite uma data")
            return
        
        try:
            date_obj = datetime.date.fromisoformat(date_str)
        except ValueError:
            messagebox.showerror("Erro", "Data inválida. Use AAAA-MM-DD")
            return
        
        success, msg = add_holiday(date_obj)
        
        if success:
            messagebox.showinfo("✓ Sucesso", msg)
            self.holiday_date_entry.delete(0, "end")
        else:
            messagebox.showerror("✗ Erro", msg)

    # ============ LOGS DE AUDITORIA (ADMIN) ============
    def init_logs_tab(self):
        """Inicializa a aba de logs de auditoria"""
        tab = self.tabview.tab("📋 Logs de Auditoria")
        
        # Card de controles
        control_card = ctk.CTkFrame(tab, fg_color=COLORS['card'], corner_radius=10)
        control_card.pack(fill="x", pady=10, padx=10)
        
        frame_controls = ctk.CTkFrame(control_card, fg_color="transparent")
        frame_controls.pack(fill="x", pady=15, padx=15)
        
        # Categoria
        ctk.CTkLabel(frame_controls, text="Categoria:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=5)
        self.logs_categoria_var = ctk.StringVar(value="")
        self.logs_categoria_combo = ctk.CTkComboBox(
            frame_controls,
            values=["", "funcionario", "evento", "feriado", "folga", "usuario", "autenticacao"],
            variable=self.logs_categoria_var,
            width=120,
            border_color=COLORS['primary'],
            button_color=COLORS['primary']
        )
        self.logs_categoria_combo.pack(side="left", padx=5)
        
        # Usuário
        ctk.CTkLabel(frame_controls, text="Usuário:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(20, 5))
        self.logs_usuario_var = ctk.StringVar()
        self.logs_usuario_entry = ctk.CTkEntry(
            frame_controls,
            placeholder_text="Filtrar por usuário",
            width=120,
            border_color=COLORS['primary']
        )
        self.logs_usuario_entry.pack(side="left", padx=5)
        
        # Botões
        ctk.CTkButton(
            frame_controls,
            text="🔍 Filtrar",
            command=self.load_logs,
            width=100,
            fg_color=COLORS['primary'],
            hover_color=COLORS['secondary']
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            frame_controls,
            text="🔄 Atualizar",
            command=self.load_logs,
            width=100,
            fg_color=COLORS['accent'],
            hover_color='#0097A7'
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            frame_controls,
            text="🗑️ Limpar (>90 dias)",
            command=self.clear_old_logs_action,
            width=160,
            fg_color=COLORS['warning'],
            hover_color='#F57C00'
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            frame_controls,
            text="📄 Exportar PDF",
            command=self.export_logs_pdf,
            width=120,
            fg_color=COLORS['warning'],
            hover_color='#F57C00'
        ).pack(side="right", padx=10)
        
        # Card de resumo
        self.logs_summary_card = ctk.CTkFrame(tab, fg_color=COLORS['background'], corner_radius=10)
        self.logs_summary_card.pack(fill="x", pady=5, padx=10)
        
        self.logs_summary_label = ctk.CTkLabel(
            self.logs_summary_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text']
        )
        self.logs_summary_label.pack(pady=10, padx=15)
        
        # Treeview
        tree_frame = ctk.CTkFrame(tab, fg_color=COLORS['card'])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ["Timestamp", "Usuário", "Categoria", "Ação", "Status", "Detalhes"]
        self.logs_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.logs_tree.heading(col, text=col)
            if col == "Timestamp":
                self.logs_tree.column(col, width=140, anchor="center")
            elif col == "Usuário":
                self.logs_tree.column(col, width=100, anchor="center")
            elif col == "Categoria":
                self.logs_tree.column(col, width=100, anchor="center")
            elif col == "Status":
                self.logs_tree.column(col, width=80, anchor="center")
            else:
                self.logs_tree.column(col, width=150, anchor="w")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.logs_tree.yview)
        self.logs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.logs_tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # Estilo da Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                       background="white",
                       foreground=COLORS['text'],
                       rowheight=25,
                       fieldbackground="white",
                       font=('Arial', 9))
        style.configure("Treeview.Heading",
                       background=COLORS['primary'],
                       foreground="white",
                       font=('Arial', 10, 'bold'))
        style.map('Treeview', background=[('selected', COLORS['accent'])])
        
        # Carregar logs inicialmente
        self.load_logs()

    def load_logs(self):
        """Carrega os logs de auditoria com filtros"""
        categoria = self.logs_categoria_var.get() or None
        usuario = self.logs_usuario_entry.get().strip() or None
        
        logs = get_logs(limit=500, categoria=categoria, usuario=usuario)
        summary = get_logs_summary()
        
        # Atualizar resumo
        summary_text = "Resumo: "
        if summary:
            parts = []
            for cat, statuses in summary.items():
                total = statuses.get('sucesso', 0) + statuses.get('falha', 0)
                parts.append(f"{cat}: {total}")
            summary_text += " | ".join(parts)
        else:
            summary_text += "Sem registros"
        
        self.logs_summary_label.configure(text=summary_text)
        
        # Atualizar treeview
        self.logs_tree.delete(*self.logs_tree.get_children())
        
        for log in logs:
            bg = "white"
            if log['status'] == 'falha':
                bg = "#FFEBEE"
            
            item = self.logs_tree.insert("", "end", values=[
                log['timestamp'][:19],  # Sem microsegundos
                log['usuario'],
                log['categoria'],
                log['acao'][:40],  # Truncar se muito longo
                log['status'].upper(),
                log['detalhes'][:50] if log['detalhes'] else '-'
            ])
            
            if bg != "white":
                self.logs_tree.tag_configure(f'bg_{item}', background=bg)
                self.logs_tree.item(item, tags=(f'bg_{item}',))

    def clear_old_logs_action(self):
        """Limpa logs antigos"""
        confirm = messagebox.askyesno(
            "⚠️ Confirmar Limpeza",
            "Deseja realmente remover logs com mais de 90 dias?\n\n"
            "Esta ação não pode ser desfeita!"
        )
        
        if not confirm:
            return
        
        count = clear_old_logs(days=90)
        if count > 0:
            messagebox.showinfo("✓ Limpeza Concluída", f"{count} registros de log removidos com sucesso!")
        else:
            messagebox.showinfo("ℹ️ Limpeza", "Nenhum log antigo encontrado para remover.")
        
        # Atualizar a visualização
        self.load_logs()


if __name__ == "__main__":
    app = PontoFlowApp(is_admin=True, current_user="admin")
    app.mainloop()
