#!/usr/bin/env python
import gi
import os
import json
import subprocess
import base64
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

Adw.init()

SESSIONS_FILE = Path.home() / ".config/ssh-manager/sessions.json"
SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

import gi.repository.Gdk as Gdk

class SSHSessionManager(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.example.SSHManager")
        self.sessions = []

    def load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data('''
            .session-label-bg {
                background-color: #0d6efd; /* mesma cor do botão editar */
                padding: 4px 8px;
                border-radius: 6px;
                color: white;
            }
            .session-label {
                font-size: 1.1em;
                font-weight: 500;
                color: white;
            }
            entry.error, passwordentry.error {
                border: 2px solid #dc3545;
                border-radius: 4px;
            }
            button.error {
                background-color: #dc3545;
                color: white;
            }
            button.quit {
                background-color: #dc3545;
                color: white;
            }
            button.connect:hover {
                background-color: #28a745;
                color: white;
            }
            button.edit:hover {
                background-color: #0d6efd;
                color: white;
            }
            button.save {
                background-color: #0d6efd;
                color: white;
            }
            button.quit:hover {
                background-color: #dc3545;
                color: white;
            }
            button.delete:hover {
                background-color: #dc3545;
                color: white;
            }
            button.duplicate:hover {
                background-color: #ffc107;
                color: black;
            }
            /* Adicionar controle explícito de tamanho com CSS */
            .small-entry {
                max-width: 200px;
                min-width: 150px;
            }
            .large-entry {
                min-width: 300px;
            }
            /* Novo estilo para o contêiner de formulário alinhado à direita */
            .right-aligned-form {
                margin-left: auto;
                margin-right: 0;
            }
        '''.encode('utf-8'))
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        self.load_css()
        self.load_sessions()

        win = Gtk.ApplicationWindow(application=self)
        
        win.set_title("Gerenciador de Sessões SSH")
        win.set_default_size(700, 220)
        win.set_resizable(True)
        win.set_hide_on_close(False)

        main_grid = Gtk.Grid(column_spacing=24, row_spacing=12, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        win.set_child(main_grid)

        # Área da lista
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.list_container = Gtk.ListBox()
        self.list_container.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.append(self.list_container)
        main_grid.attach(list_box, 0, 0, 1, 1)

        # Área do formulário - Contêiner principal para alinhamento à direita
        form_container_outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        
        # Espaçador flexível à esquerda para empurrar o conteúdo para a direita
        spacer = Gtk.Box(hexpand=True)
        form_container_outer.append(spacer)
        
        # Contêiner real do formulário (agora alinhado à direita devido ao espaçador)
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=False)
        form_box.add_css_class("right-aligned-form")
        form_container_outer.append(form_box)

        # Definir o tamanho inicial como 10 caracteres e adicionar classe CSS
        self.name_entry = Gtk.Entry(placeholder_text="Nome da Sessão", width_chars=10, max_width_chars=15)
        self.name_entry.set_tooltip_text("Informe um nome identificador para a sessão.")
        self.name_entry.add_css_class("small-entry")
        
        self.userhost_entry = Gtk.Entry(placeholder_text="usuario@host", width_chars=10, max_width_chars=15)
        self.userhost_entry.set_tooltip_text("Formato esperado: usuario@ip ou usuario@host")
        self.userhost_entry.add_css_class("small-entry")

        self.auth_type_combo = Gtk.DropDown.new_from_strings(["Chave privada", "Senha"])
        self.auth_type_combo.set_selected(0)
        self.auth_type_combo.connect("notify::selected", self.on_auth_type_changed)

        self.key_file_button = Gtk.Button(label="Selecionar chave")
        self.key_file_button.set_tooltip_text("Selecione a chave privada para autenticação SSH.")
        self.key_file_button.connect("clicked", self.on_select_file)

        self.password_entry = Gtk.PasswordEntry(placeholder_text="Senha", width_chars=10, max_width_chars=15)
        self.password_entry.set_tooltip_text("Informe a senha para autenticação se aplicável.")
        self.password_entry.add_css_class("small-entry")

        # Contêiner para botões com alinhamento à direita
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.END)
        
        self.save_button = Gtk.Button(label="Salvar Sessão")
        self.save_button.add_css_class("save")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self.on_save)

        self.cancel_button = Gtk.Button(label="Cancelar")
        self.cancel_button.connect("clicked", self.on_cancel_edit)
        self.cancel_button.set_visible(False)

        self.quit_button = Gtk.Button(label="Sair")
        self.quit_button.add_css_class("quit")
        self.quit_button.add_css_class("destructive-action")
        self.quit_button.connect("clicked", lambda b: self.quit())

        # Adiciona os botões ao button_box
        button_box.append(self.save_button)
        button_box.append(self.cancel_button)
        button_box.append(self.quit_button)

        # Monitorar alterações nos campos para habilitar o botão salvar
        for entry in [self.name_entry, self.userhost_entry, self.password_entry]:
            entry.connect("notify::text", self.on_form_changed)
        self.auth_type_combo.connect("notify::selected", self.on_form_changed)

        # Adiciona todos os widgets ao form_box
        for widget in [self.name_entry, self.userhost_entry, self.auth_type_combo, 
                      self.key_file_button, self.password_entry, button_box]:
            form_box.append(widget)

        main_grid.attach(form_container_outer, 1, 0, 1, 1)

        self.on_auth_type_changed()
        self.refresh_sessions()
        win.present()

    def on_select_file(self, button):
        dialog = Gtk.FileDialog()
        dialog.open(self.get_active_window(), None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.selected_file = file.get_path()
            else:
                self.selected_file = ""
        except Exception:
            self.selected_file = ""

    def on_form_changed(self, *args):
        name_filled = self.name_entry.get_text().strip() != ""
        userhost_filled = self.userhost_entry.get_text().strip() != ""
        password_filled = self.password_entry.get_text().strip() != ""
        auth_type = self.auth_type_combo.get_selected()
        key_filled = hasattr(self, "selected_file") and self.selected_file.strip() != ""

        if auth_type == 0:
            valid = name_filled and userhost_filled and key_filled
        else:
            valid = name_filled and userhost_filled and password_filled

        self.save_button.set_sensitive(valid)

    def on_auth_type_changed(self, *args):
        use_key = self.auth_type_combo.get_selected() == 0
        self.key_file_button.set_sensitive(use_key)
        self.password_entry.set_sensitive(not use_key)

    def on_cancel_edit(self, button):
        self.cancel_button.set_visible(False)

        # Restaura a sessão original se estava editando
        if hasattr(self, 'editing_session_backup'):
            self.sessions.append(self.editing_session_backup)
            self.save_sessions()
            self.refresh_sessions()
            del self.editing_session_backup

    def on_save(self, button):
        name = self.name_entry.get_text().strip()
        userhost = self.userhost_entry.get_text().strip()
        auth_type = "key" if self.auth_type_combo.get_selected() == 0 else "password"
        password = self.password_entry.get_text().strip()
        key_path = getattr(self, "selected_file", "") if auth_type == "key" else ""

        # Reset styles
        for entry in [self.name_entry, self.userhost_entry, self.password_entry]:
            entry.remove_css_class("error")

        # Validação
        invalid = False
        if not name:
            self.name_entry.add_css_class("error")
            invalid = True
        if not userhost:
            self.userhost_entry.add_css_class("error")
            invalid = True
        if auth_type == "key" and not key_path:
            self.key_file_button.add_css_class("error")
            invalid = True
        elif auth_type == "password" and not password:
            self.password_entry.add_css_class("error")
            invalid = True

        if any(sess["name"] == name for sess in self.sessions):
            self.name_entry.add_css_class("error")
            error_dialog = Gtk.AlertDialog()
            error_dialog.set_modal(True)
            error_dialog.set_heading("Nome de sessão duplicado")
            error_dialog.set_body("Já existe uma sessão com esse nome. Escolha um nome diferente.")
            error_dialog.add_response("ok", "Ok")
            error_dialog.choose(self.get_active_window())
            return

        if invalid:
            error_dialog = Gtk.AlertDialog()
            error_dialog.set_modal(True)
            error_dialog.set_heading("Preencha todos os campos obrigatórios")
            error_dialog.set_body("Verifique os campos destacados e tente novamente.")
            error_dialog.add_response("ok", "Ok")
            error_dialog.choose(self.get_active_window())
            return

        session = {
            "name": name,
            "userhost": userhost,
            "auth_type": auth_type,
            "key_path": key_path,
            "password": base64.b64encode(password.encode()).decode() if auth_type == "password" else ""
        }

        self.sessions.append(session)
        self.save_sessions()
        self.refresh_sessions()
        self.name_entry.set_text("")
        self.userhost_entry.set_text("")
        self.password_entry.set_text("")

    def refresh_sessions(self):
        children = list(self.list_container)
        for child in children:
            self.list_container.remove(child)

        # Ajustar tamanho dos campos com base na existência de sessões
        if not self.sessions:
            self.list_container.append(Gtk.Label(label="Nenhuma sessão cadastrada."))
            
            # Para campos vazios, usar classe small-entry e definir tamanhos pequenos
            for entry in [self.name_entry, self.userhost_entry, self.password_entry]:
                entry.remove_css_class("large-entry")
                entry.add_css_class("small-entry")
                entry.set_width_chars(40)
                entry.set_max_width_chars(15)
        else:
            # Para quando há sessões, usar classe large-entry e definir tamanhos maiores
            for entry in [self.name_entry, self.userhost_entry, self.password_entry]:
                entry.remove_css_class("small-entry")
                entry.add_css_class("large-entry")
                entry.set_width_chars(25)
                entry.set_max_width_chars(30)

        for index, session in enumerate(self.sessions):
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            label = Gtk.Label(label=f"  {session['name']}")  # Nerd Font ícone de computador + nome
            label.set_xalign(0)
            label.set_css_classes(["session-label", "session-label-bg"])
            label.set_hexpand(True)
            label.set_xalign(0)

            connect_btn = Gtk.Button(label="Conectar")
            connect_btn.add_css_class("connect")
            connect_btn.connect("clicked", self.on_connect_clicked, session)

            edit_btn = Gtk.Button(label="Editar")
            edit_btn.add_css_class("edit")
            edit_btn.connect("clicked", self.on_edit_clicked, index)

            duplicate_btn = Gtk.Button(label="Duplicar")
            duplicate_btn.add_css_class("duplicate")
            duplicate_btn.connect("clicked", self.on_duplicate_clicked, session)

            delete_btn = Gtk.Button(label="Excluir")
            delete_btn.add_css_class("delete")
            delete_btn.connect("clicked", self.on_delete_clicked, index)

            row_box.append(label)
            row_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
            row_box.append(connect_btn)
            row_box.append(edit_btn)
            row_box.append(duplicate_btn)
            row_box.append(delete_btn)

            self.list_container.append(row_box)

    def on_edit_clicked(self, button, index):
        session = self.sessions[index]
        self.editing_session_backup = session.copy()

        dialog = Gtk.MessageDialog(
            transient_for=self.get_active_window(),
            modal=True,
            buttons=Gtk.ButtonsType.YES_NO,
            message_type=Gtk.MessageType.QUESTION,
            text="Confirmar edição",
            secondary_text="Deseja editar esta sessão?"
        )

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.YES:
                self.name_entry.set_text(session["name"])
                self.cancel_button.set_visible(True)
                self.userhost_entry.set_text(session["userhost"])
                self.auth_type_combo.set_selected(0 if session["auth_type"] == "key" else 1)
                if session["auth_type"] == "key":
                    self.selected_file = session["key_path"]
                else:
                    self.password_entry.set_text(base64.b64decode(session["password"]).decode())
                del self.sessions[index]
                self.save_sessions()
                self.refresh_sessions()
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def on_duplicate_clicked(self, button, session):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_active_window(),
            modal=True,
            buttons=Gtk.ButtonsType.YES_NO,
            message_type=Gtk.MessageType.QUESTION,
            text="Confirmar duplicação",
            secondary_text="Deseja duplicar esta sessão?"
        )

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.YES:
                new_session = session.copy()
                new_session["name"] = session["name"] + " (cópia)"
                self.sessions.append(new_session)
                self.save_sessions()
                self.refresh_sessions()
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def on_delete_clicked(self, button, index):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_active_window(),
            modal=True,
            buttons=Gtk.ButtonsType.YES_NO,
            message_type=Gtk.MessageType.QUESTION,
            text="Confirmação de exclusão",
            secondary_text="Tem certeza que deseja excluir esta sessão?"
        )

        def on_response(dlg, response_id):
            if response_id == Gtk.ResponseType.YES:
                del self.sessions[index]
                self.save_sessions()
                self.refresh_sessions()
            dlg.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def on_connect_clicked(self, button, session):
        password = base64.b64decode(session["password"]).decode() if session["auth_type"] == "password" else ""
        if session["auth_type"] == "key":
            cmd = ["terminator", "--new-tab", "-x", "ssh", "-i", session["key_path"], session["userhost"]]
        else:
            cmd = ["terminator", "--new-tab", "-x", "sshpass", "-p", password, "ssh", session["userhost"]]
        subprocess.Popen(cmd)

    def load_sessions(self):
        if SESSIONS_FILE.exists():
            try:
                with open(SESSIONS_FILE, 'r') as f:
                    self.sessions = json.load(f)
            except Exception:
                self.sessions = []

    def save_sessions(self):
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(self.sessions, f, indent=2)


app = SSHSessionManager()
app.run()
