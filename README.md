# ⏱️ Marc - Sistema de Ponto Eletrônico Offline

**Marc** é um sistema de gestão de ponto eletrônico desenvolvido em **Python** com foco principal em **segurança, auditoria rigorosa e manutenção de dados** em ambiente **offline**.

Embora inicialmente concebido como um projeto comercial, ele está sendo disponibilizado como uma solução robusta e confiável para controle de jornada de trabalho.

---

## 💡 Visão Geral do Sistema

O Marc gerencia o registro de eventos de ponto (entrada, pausas, saída), controle de funcionários, feriados e folgas, com um forte componente de auditoria e backups automáticos do banco de dados.

### 🧱 Arquitetura Modular

O sistema é estruturado em cinco módulos principais, garantindo clara separação de responsabilidades:

| Módulo | Função Principal |
| :--- | :--- |
| `main.py` | Ponto de entrada, autenticação e inicialização do sistema. |
| `gui.py` | Interface Gráfica do Usuário (GUI) construída com `CustomTkinter`. |
| `db.py` | Gerenciamento da persistência de dados no **SQLite**. |
| `core_db.py` | Regras de negócio, lógica de cálculo e manipulação de dados centrais. |
| `backup.py` | Sistema de **backup automático** e verificação de integridade do DB. |

---

## 🔒 Segurança e Autenticação

- **Criptografia de Senhas:** Utiliza **`bcrypt`** para armazenamento seguro de credenciais.
- **Controle de Acesso:** Dois níveis de acesso: **Administrador** (gestão total) e **Funcionário** (registro de ponto e visualização própria).
- **Auditoria:** O usuário logado é sempre rastreado para cada ação crítica no sistema.

---

## 📋 Funcionalidades Chave

### 1. Gestão de Ponto
- **Registro Completo:** Entrada, Início/Fim de Descanso e Saída.
- **Validação Lógica:** Garante a sequência correta dos eventos de ponto.
- **Ajuste de Eventos:** Possibilidade de ajustes mediante justificativa e aprovação administrativa.

### 2. Administração de Pessoal
- Cadastro, listagem e remoção de funcionários (com exclusão de dados relacionados).

### 3. Calendário e Ausências
- Cadastro de **Feriados** nacionais/regionais.
- Definição de **Folgas Individuais** por funcionário.

### 4. Relatórios de Ponto e Exportação
- Visualização detalhada por funcionário/mês.
- **Cálculo Automático** de horas trabalhadas.
- Exportação da Folha de Ponto para **PDF** com layout profissional.

### 5. Logs de Auditoria (Compliance)
- Registro detalhado de **TODA** ação no sistema (timestamp, usuário, ação, categoria, status).
- Visualização e **Exportação para PDF** organizada e paginada.
- **Limpeza Automática** de logs antigos (padrão: 90 dias).

### 6. Backup Automático
- Backups agendados (Diário/Semanal) do banco de dados SQLite.
- Verificação de integridade e funcionalidade de restauração com salvaguarda prévia.

---

## 🎨 Interface Gráfica (GUI)

Desenvolvida com **`CustomTkinter`** para um visual moderno e responsivo, organizada em abas intuitivas para cada funcionalidade.

---

## 🗄️ Banco de Dados

Utiliza **SQLite** para garantir operação totalmente **offline** e fácil portabilidade.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3**
- **CustomTkinter** (GUI)
- **SQLite** (Persistência)
- **bcrypt** (Segurança de Hash)
- **reportlab** (Geração de PDFs)
- **datetime, threading, os, shutil** (Utilitários)
