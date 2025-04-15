# 🔐 SSH Session Manager (GTK 4 + Adwaita)

Um gerenciador de sessões SSH gráfico, simples e funcional, criado com **Python**, **GTK 4** e **LibAdwaita**. Permite salvar, editar, duplicar e remover conexões SSH facilmente, com suporte a autenticação por **chave privada** ou **senha**.

---

## ✨ Funcionalidades

- 💾 Salvar conexões SSH com nome amigável
- 🔑 Suporte a autenticação via chave privada ou senha
- 📋 Listagem de sessões com botões de:
  - 🔄 **Duplicar**
  - ✏️ **Editar**
  - 🚀 **Conectar**
  - ❌ **Excluir**
- ✅ Confirmação antes de excluir ou duplicar sessões
- 🧩 Interface moderna usando Adwaita e GTK 4
- 🗂️ Armazenamento local das sessões em `~/.config/ssh-manager/sessions.json`
- 🛡️ Senha criptografada em base64 (para ofuscação)

---

## 🖼️ Captura de tela

![alt text](image.png)

![alt text](image-1.png)


![alt text](image-2.png)


---

## 💻 Requisitos

### Arch Linux / Manjaro

```bash
sudo pacman -S gtk4 libadwaita python-gobject terminator sshpass