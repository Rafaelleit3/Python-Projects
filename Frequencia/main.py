import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import sqlite3
from tkinter import messagebox
import pandas as pd
import os
import cv2
import PIL.Image, PIL.ImageTk
from datetime import datetime
from pyzbar.pyzbar import decode as lerqrcode


# ler qrCode

def ler_qr_code(frame):
    decoded_objects = lerqrcode(frame)
    for obj in decoded_objects:
        return obj.data.decode('utf-8')
    return None


def atualizar_banco_dados(dados):
    conn = sqlite3.connect('dados_qrcode.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS presencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            disciplina TEXT,
            turma TEXT,
            turno TEXT,
            sala TEXT,
            aluno TEXT,
            status TEXT
        )
    ''')

    aluno, data, disciplina, turma, turno, sala = dados
    cursor.execute('''
        SELECT * FROM presencas WHERE 
        data = ? AND 
        disciplina = ? AND 
        turma = ? AND 
        turno = ? AND 
        sala = ? AND 
        aluno = ?
    ''', (data, disciplina, turma, turno, sala, aluno))
    
    if cursor.fetchone():
        conn.close()
        return "Matrícula já foi lida."

    cursor.execute('''
        INSERT INTO presencas (data, disciplina, turma, turno, sala, aluno, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data, disciplina, turma, turno, sala, aluno, 'presente'))

    conn.commit()
    conn.close()
    return f"Dados salvos: {dados}"


def fetch_disciplines():
    conn = sqlite3.connect("dados_qrcode.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT disciplina FROM presencas")
    disciplines = [row[0] for row in cursor.fetchall()]
    conn.close()
    return disciplines

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Menu Principal")
        self.root.geometry("400x300")
        self.style = ttk.Style("cosmo")

        self.container = ttk.Frame(self.root, padding="10")
        self.container.grid(row=0, column=0, sticky="nsew")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.release_button = ttk.Button(self.container, text="Lançamentos", command=self.run_release)
        self.release_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.filter_button = ttk.Button(self.container, text="Exportar", command=self.run_filter)
        self.filter_button.grid(row=1, column=0, padx=5, pady=10, sticky="ew")

    def run_release(self):
        self.hide_main()
        run_release_app(self.show_main)

    def run_filter(self):
        self.hide_main()
        run_filter_app(self.show_main)

    def hide_main(self):
        self.root.withdraw()

    def show_main(self):
        self.root.update()
        self.root.deiconify()

def run_release_app(callback):
    release_window = tk.Toplevel()
    release_window.title("Realizar Frequência")
    release_window.geometry("800x600")

    def on_closing():
        release_window.destroy()
        callback()

    release_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Função para criar um frame com uma label e um entry
    def create_input_frame(window, label_text):
        frame = ttk.Frame(window)
        frame.pack(pady=5, padx=5, fill='x')
        ttk.Label(frame, text=label_text, width=15).pack(side="left")
        entry = ttk.Entry(frame)
        entry.pack(side="left", fill='x', expand=True)
        return entry

    # Labels e Entradas
    disciplina_entry = create_input_frame(release_window, "Disciplina")
    turma_entry = create_input_frame(release_window, "Turma")
    turno_entry = create_input_frame(release_window, "Turno")
    sala_entry = create_input_frame(release_window, "Sala")

    # Status e lista de alunos
    status_var = tk.StringVar()
    alunos_lidos = []

    #frame para botões
    button_frame = ttk.Frame(release_window)
    button_frame.pack(pady=10)

    # Botão de submissão
    ttk.Button(button_frame, text="Ler QR", command=lambda: start_camera(release_window)).pack(side="left",padx=5)
    ttk.Button(button_frame, text="Salvar", command=lambda: on_submit(disciplina_entry, turma_entry, turno_entry, sala_entry, alunos_lidos, status_var)).pack(side="left",padx=5)

    # Botão de retorno
    ttk.Button(release_window, text="Voltar", command=lambda: [release_window.destroy(), callback()]).pack(pady=20)

    cap = None
    canvas = None
    frame = None

    # Status label
    status_label = ttk.Label(release_window, textvariable=status_var, foreground="red")
    status_label.pack(pady=5)

    # Lista de alunos
    columns = ("aluno",)
    alunos_listbox = ttk.Treeview(release_window, columns=columns, show="headings")
    for col in columns:
        alunos_listbox.heading(col, text=col)
    alunos_listbox.pack(expand=True, fill="both", padx=10, pady=10)

    def start_camera(window):
        nonlocal cap, canvas
        if not cap:
            cap = cv2.VideoCapture(0)
            canvas = tk.Canvas(window, width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            canvas.pack(pady=10)
            update_frame(window)

    def update_frame(window):
        nonlocal cap, frame
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(frame)
            imgtk = PIL.ImageTk.PhotoImage(image=img)
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            canvas.image = imgtk

            aluno = ler_qr_code(frame)
            if aluno:
                if aluno not in alunos_lidos:
                    alunos_lidos.append(aluno)
                    alunos_listbox.insert("", tk.END, values=(aluno,))
                    status_var.set("")
                else:
                    status_var.set("Matrícula já foi lida.")

        window.after(10, lambda: update_frame(window))

    def on_submit(disciplina_entry, turma_entry, turno_entry, sala_entry, alunos_lidos, status_var):
        disciplina = disciplina_entry.get()
        turma = turma_entry.get()
        turno = turno_entry.get()
        sala = sala_entry.get()
        data = datetime.now().strftime("%d/%m/%Y")

        for aluno in alunos_lidos:
            dados = (aluno, data, disciplina, turma, turno, sala)
            status = atualizar_banco_dados(dados)
            status_var.set(status)

            
def run_filter_app(callback):
    def search():
        date = date_entry.get()
        discipline = discipline_combobox.get()
        if not date or not discipline:
            messagebox.showwarning("Campos obrigatórios", "Por favor, preencha todos os campos.")
            return

        conn = sqlite3.connect("dados_qrcode.db")
        cursor = conn.cursor()
        query = """
        SELECT * FROM presencas WHERE data = ? AND disciplina = ?
        """
        cursor.execute(query, (date, discipline))
        records = cursor.fetchall()
        conn.close()

        for row in tree.get_children():
            tree.delete(row)
        for record in records:
            tree.insert("", "end", values=record)

    def export_to_excel():
        date = date_entry.get()
        discipline = discipline_combobox.get()
        if not date or not discipline:
            messagebox.showwarning("Campos obrigatórios", "Por favor, preencha todos os campos.")
            return

        conn = sqlite3.connect("dados_qrcode.db")
        cursor = conn.cursor()
        query = """
        SELECT * FROM presencas WHERE data = ? AND disciplina = ?
        """
        cursor.execute(query, (date, discipline))
        records = cursor.fetchall()
        conn.close()

        if not records:
            messagebox.showinfo("Sem dados", "Nenhum dado encontrado para os critérios informados.")
            return

        df = pd.DataFrame(records, columns=["id", "data", "disciplina", "turma", "sala", "turno", "aluno", "status"])
        output_directory = "arquivos/relatorios"
        os.makedirs(output_directory, exist_ok=True)  # Criar o diretório se não existir
        safe_date = date.replace("/", "-")
        file_path = f"{output_directory}/relatorio_{safe_date}_{discipline}.xlsx"
        df.to_excel(file_path, index=False)  # Escrever um novo arquivo, substituindo qualquer arquivo existente
        messagebox.showinfo("Exportação bem-sucedida", f"Dados exportados para {file_path}")

    filter_window = tk.Toplevel()
    filter_window.title("Filtrar Dados")
    filter_window.geometry("800x600")

    def on_closing():
        filter_window.destroy()
        callback()

    filter_window.protocol("WM_DELETE_WINDOW", on_closing)

    ttk.Label(filter_window, text="Data (dd/mm/aaaa):").pack(pady=5)
    date_entry = ttk.Entry(filter_window)
    date_entry.pack(pady=5)

    ttk.Label(filter_window, text="Disciplina:").pack(pady=5)
    disciplines = fetch_disciplines()
    discipline_combobox = ttk.Combobox(filter_window, values=disciplines)
    discipline_combobox.pack(pady=5)

    ttk.Button(filter_window, text="Buscar", command=search).pack(pady=10)

    columns = ("id", "data", "disciplina", "turma", "sala", "turno", "aluno", "status")
    tree = ttk.Treeview(filter_window, columns=columns, show="headings")

    for col in columns:
        tree.heading(col, text=col, anchor="center")  # Centraliza o título da coluna
        tree.column(col, width=100, anchor="center")  # Centraliza o texto na coluna

    tree.pack(expand=True, fill="both", padx=10, pady=10)

    ttk.Button(filter_window, text="Exportar para Excel", command=export_to_excel).pack(pady=10)
    ttk.Button(filter_window, text="Voltar", command=lambda: [filter_window.destroy(), callback()]).pack(pady=10)

def run_main_app():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_main_app()
