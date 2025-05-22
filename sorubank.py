import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time

# Veritabanı bağlantısı
def connect_db():
    retries = 5
    for _ in range(retries):
        try:
            conn = sqlite3.connect('questions.db')
            return conn
        except sqlite3.OperationalError:
            time.sleep(1)
    raise Exception("Veritabanına bağlanılamadı.")

def create_database():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT,
        correct_answer INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        option_text TEXT,
        FOREIGN KEY (question_id) REFERENCES questions(id))''')
    conn.commit()
    conn.close()

# PDF'e dönüştürme
def save_question_as_pdf(question_text, options, correct_answer, file_name="question.pdf"):
    c = canvas.Canvas(file_name, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Soru: {question_text}")
    y = 730
    for idx, option in enumerate(options):
        _, _, text = option
        y -= 20
        c.drawString(100, y, f"Şık {idx+1}: {text}")
    c.drawString(100, y - 40, f"Doğru Cevap: Şık {correct_answer}")
    c.save()

# Yeni soru ekleme arayüzü
def add_new_question(window):
    def save_question():
        question_text = question_entry.get()
        correct_answer = int(correct_answer_entry.get())
        options = [option1.get(), option2.get(), option3.get(), option4.get()]
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO questions (question_text, correct_answer) VALUES (?, ?)", (question_text, correct_answer))
        qid = cursor.lastrowid
        for opt in options:
            cursor.execute("INSERT INTO options (question_id, option_text) VALUES (?, ?)", (qid, opt))
        conn.commit()
        conn.close()
        messagebox.showinfo("Başarılı", "Soru eklendi.")
        add_win.destroy()

    add_win = tk.Toplevel(window)
    add_win.title("Yeni Soru Ekle")

    tk.Label(add_win, text="Soru:").pack()
    question_entry = tk.Entry(add_win, width=50)
    question_entry.pack()

    option1 = tk.Entry(add_win, width=50)
    option2 = tk.Entry(add_win, width=50)
    option3 = tk.Entry(add_win, width=50)
    option4 = tk.Entry(add_win, width=50)
    for i, opt in enumerate([option1, option2, option3, option4], 1):
        tk.Label(add_win, text=f"Şık {i}:").pack()
        opt.pack()

    tk.Label(add_win, text="Doğru Şık (1-4):").pack()
    correct_answer_entry = tk.Entry(add_win, width=5)
    correct_answer_entry.pack()

    tk.Button(add_win, text="Kaydet", command=save_question).pack(pady=10)

# Soruları listeleme ve PDF/sil işlemleri
def show_question_list(window):
    list_win = tk.Toplevel(window)
    list_win.title("Sorular Listesi")
    list_win.geometry("600x400")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    listbox = tk.Listbox(list_win, width=80)
    listbox.pack(pady=10)
    for q in questions:
        listbox.insert(tk.END, f"{q[0]} - {q[1]}")

    def delete_selected():
        selected = listbox.curselection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen bir soru seçin.")
            return
        index = selected[0]
        question_id = questions[index][0]
        if messagebox.askyesno("Onay", "Soruyu silmek istediğinize emin misiniz?"):
            cursor.execute("DELETE FROM options WHERE question_id=?", (question_id,))
            cursor.execute("DELETE FROM questions WHERE id=?", (question_id,))
            conn.commit()
            listbox.delete(index)
            messagebox.showinfo("Başarılı", "Soru silindi.")

    def export_pdf():
        selected = listbox.curselection()
        if not selected:
            messagebox.showwarning("Uyarı", "Lütfen bir soru seçin.")
            return
        index = selected[0]
        question_id = questions[index][0]
        cursor.execute("SELECT * FROM questions WHERE id=?", (question_id,))
        question = cursor.fetchone()
        cursor.execute("SELECT * FROM options WHERE question_id=?", (question_id,))
        options = cursor.fetchall()
        save_question_as_pdf(question[1], options, question[2])
        messagebox.showinfo("PDF Oluşturuldu", "Soru PDF olarak kaydedildi.")

    tk.Button(list_win, text="PDF'e Dönüştür", command=export_pdf).pack(pady=5)
    tk.Button(list_win, text="Soru Sil", command=delete_selected).pack(pady=5)

# Soruları sırayla çözme
def solve_questions(window):
    solve_win = tk.Toplevel(window)
    solve_win.title("Soruları Çöz")
    solve_win.geometry("600x300")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    current_index = [0]

    question_label = tk.Label(solve_win, text="", wraplength=550)
    question_label.pack(pady=10)
    answer_var = tk.IntVar()
    radio_buttons = [tk.Radiobutton(solve_win, variable=answer_var, value=i+1, text="") for i in range(4)]
    for rb in radio_buttons:
        rb.pack(anchor='w')

    def load_question():
        if current_index[0] >= len(questions):
            messagebox.showinfo("Bitti", "Tüm sorular çözüldü.")
            solve_win.destroy()
            return
        question = questions[current_index[0]]
        cursor.execute("SELECT * FROM options WHERE question_id=?", (question[0],))
        options = cursor.fetchall()
        question_label.config(text=f"Soru: {question[1]}")
        for i in range(4):
            radio_buttons[i].config(text=options[i][2])
        answer_var.set(0)

    def check_answer():
        selected = answer_var.get()
        correct = questions[current_index[0]][2]
        if selected == correct:
            messagebox.showinfo("Doğru", "Tebrikler, doğru cevap!")
        else:
            messagebox.showerror("Yanlış", f"Yanlış cevap. Doğru cevap: Şık {correct}")
        current_index[0] += 1
        load_question()

    tk.Button(solve_win, text="Cevapla", command=check_answer).pack(pady=10)
    load_question()

# Ana pencere
def main_window():
    root = tk.Tk()
    root.title("Soru Bankası")
    root.geometry("400x300")

    tk.Button(root, text="Yeni Soru Ekle", width=25, command=lambda: add_new_question(root)).pack(pady=10)
    tk.Button(root, text="Soruları Göster / PDF / Sil", width=25, command=lambda: show_question_list(root)).pack(pady=10)
    tk.Button(root, text="Soruları Çöz", width=25, command=lambda: solve_questions(root)).pack(pady=10)

    root.mainloop()

# Uygulamayı başlat
create_database()
main_window()
