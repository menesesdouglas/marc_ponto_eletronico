"""
Marc - Sistema de Gestão de Ponto
Versão 1.2 - Com Autenticação Segura, Auditoria e Backup Automático
"""

import customtkinter as ctk
from tkinter import messagebox
import db
from core_db import set_current_user
from backup import BackupManager, BackupScheduler, initialize_backup_system, start_automatic_backups

# Inicializar banco de dados
db.init_db()

# Inicializar sistema de backup
backup_manager = initialize_backup_system(db_file="ponto.db", backup_dir="backups")
backup_scheduler = start_automatic_backups(backup_manager, check_interval=3600)

# Paleta de cores Marc
PONTOFLOW_COLORS = {
    'primary': '#2196F3',
    'secondary': '#1976D2',
    'success': '#4CAF50',
    'danger': '#F44336',
    'background': '#F5F7FA',
    'text': '#2C3E50',
    'accent': '#00BCD4'
}


class LoginPontoFlow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Marc - Login")
        self.geometry("450x650")
        self.resizable(False, False)
        
        # Configurar cores
        ctk.set_appearance_mode("light")
        
        # Centralizar janela
        self.center_window()
        
        # ===== ESTRUTURA PRINCIPAL =====
        # Container principal
        container = ctk.CTkFrame(self, fg_color=PONTOFLOW_COLORS['background'])
        container.pack(fill="both", expand=True)
        
        # ===== HEADER =====
        header = ctk.CTkFrame(container, fg_color=PONTOFLOW_COLORS['primary'], height=140)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="⚡ Marc",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="white"
        ).pack(pady=(25, 5))
        
        ctk.CTkLabel(
            header,
            text="Gestão de ponto que flui com você",
            font=ctk.CTkFont(size=13),
            text_color="white"
        ).pack(pady=(0, 25))
        
        # ===== FORMULÁRIO =====
        form_outer = ctk.CTkFrame(container, fg_color="transparent")
        form_outer.pack(fill="both", expand=True, pady=25, padx=30)
        
        form_card = ctk.CTkFrame(form_outer, fg_color="white", corner_radius=15)
        form_card.pack(fill="both", expand=True)
        
        # Usar grid para melhor controle
        form_card.grid_rowconfigure(0, weight=0)  # Título
        form_card.grid_rowconfigure(1, weight=0)  # Subtítulo
        form_card.grid_rowconfigure(2, weight=0)  # Label usuário
        form_card.grid_rowconfigure(3, weight=0)  # Entry usuário
        form_card.grid_rowconfigure(4, weight=0)  # Label senha
        form_card.grid_rowconfigure(5, weight=0)  # Entry senha
        form_card.grid_rowconfigure(6, weight=0)  # Botão
        form_card.grid_rowconfigure(7, weight=0)  # Info
        form_card.grid_columnconfigure(0, weight=1)
        
        row = 0
        
        # Título
        ctk.CTkLabel(
            form_card,
            text="Bem-vindo de volta!",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=PONTOFLOW_COLORS['text']
        ).grid(row=row, column=0, pady=(30, 5), padx=30, sticky="w")
        row += 1
        
        # Subtítulo
        ctk.CTkLabel(
            form_card,
            text="Faça login para continuar",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).grid(row=row, column=0, pady=(0, 25), padx=30, sticky="w")
        row += 1
        
        # Label Usuário
        ctk.CTkLabel(
            form_card,
            text="Usuário:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=PONTOFLOW_COLORS['text']
        ).grid(row=row, column=0, pady=(0, 5), padx=30, sticky="w")
        row += 1
        
        # Entry Usuário
        self.username_entry = ctk.CTkEntry(
            form_card,
            placeholder_text="Digite seu usuário",
            height=42,
            border_color=PONTOFLOW_COLORS['primary'],
            border_width=2,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.username_entry.grid(row=row, column=0, pady=(0, 15), padx=30, sticky="ew")
        row += 1
        
        # Label Senha
        ctk.CTkLabel(
            form_card,
            text="Senha:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=PONTOFLOW_COLORS['text']
        ).grid(row=row, column=0, pady=(0, 5), padx=30, sticky="w")
        row += 1
        
        # Entry Senha
        self.password_entry = ctk.CTkEntry(
            form_card,
            placeholder_text="Digite sua senha",
            show="●",
            height=42,
            border_color=PONTOFLOW_COLORS['primary'],
            border_width=2,
            corner_radius=10,
            font=ctk.CTkFont(size=14)
        )
        self.password_entry.grid(row=row, column=0, pady=(0, 20), padx=30, sticky="ew")
        self.password_entry.bind("<Return>", lambda e: self.check_password())
        row += 1
        
        # BOTÃO - COM FRAME DEDICADO
        button_frame = ctk.CTkFrame(form_card, fg_color="transparent", height=50)
        button_frame.grid(row=row, column=0, pady=(0, 20), padx=30, sticky="ew")
        button_frame.grid_propagate(False)
        button_frame.grid_columnconfigure(0, weight=1)
        
        self.login_button = ctk.CTkButton(
            button_frame,
            text="Entrar",
            command=self.check_password,
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=PONTOFLOW_COLORS['primary'],
            hover_color=PONTOFLOW_COLORS['secondary'],
            corner_radius=10
        )
        self.login_button.grid(row=0, column=0, sticky="ew")
        row += 1
        
        # ===== FOOTER =====
        footer = ctk.CTkFrame(container, fg_color="transparent", height=60)
        footer.pack(side="bottom", fill="x", pady=10)
        footer.pack_propagate(False)
        
        ctk.CTkLabel(
            footer,
            text="Marc v1.2 - Autenticação Segura com Backup Automático © 2025",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        ).pack()
        
        backup_info = backup_manager.get_backup_info()
        backup_status = f"✓ Backups automáticos: {backup_info['total_backups']} cópia(s)"
        
        ctk.CTkLabel(
            footer,
            text=backup_status,
            font=ctk.CTkFont(size=8),
            text_color="green"
        ).pack()
        
        # Focar no campo de usuário
        self.username_entry.focus()
    
    def center_window(self):
        """Centraliza a janela na tela"""
        self.update_idletasks()
        width = 450
        height = 650
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def check_password(self):
        """Verifica as credenciais e abre a aplicação apropriada"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username:
            messagebox.showwarning("Aviso", "Digite o nome de usuário")
            self.username_entry.focus()
            return
        
        if not password:
            messagebox.showwarning("Aviso", "Digite a senha")
            self.password_entry.focus()
            return
        
        # Autenticar usando o banco de dados
        success, is_admin, message = db.authenticate_user(username, password)
        
        if success:
            # Login bem-sucedido - importar GUI aqui para evitar import circular
            from gui import PontoFlowApp
            
            # Definir usuário atual para logs de auditoria
            set_current_user(username)
            
            self.destroy()
            app = PontoFlowApp(is_admin=is_admin, current_user=username)
            app.mainloop()
            
            # Parar o agendador de backups quando a aplicação fecha
            backup_scheduler.stop()
        else:
            # Falha no login
            messagebox.showerror("Erro de Autenticação", message)
            self.password_entry.delete(0, "end")
            self.username_entry.focus()


if __name__ == "__main__":
    # Configurações do CustomTkinter
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    
    print("=" * 60)
    print("🚀 Marc v1.2 - Sistema de Gestão de Ponto")
    print("=" * 60)
    print("✓ Banco de dados inicializado")
    print("✓ Sistema de backup automático iniciado")
    print(f"✓ Backups localizados em: backups/")
    print("=" * 60)
    
    # Iniciar aplicação
    try:
        login = LoginPontoFlow()
        login.mainloop()
    except KeyboardInterrupt:
        print("\n⚠️  Aplicação interrompida pelo usuário")
        backup_scheduler.stop()
    except Exception as e:
        print(f"❌ Erro na aplicação: {e}")
        backup_scheduler.stop()
