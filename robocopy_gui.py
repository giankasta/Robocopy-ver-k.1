import locale
import os
import queue
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def resource_path(filename):
    bundle_directory = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(bundle_directory, filename)


class RobocopyWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Copia file con Robocopy")
        self.root.geometry("820x700")
        self.root.minsize(680, 590)

        self.events = queue.Queue()
        self.process = None
        self.active_mode = "robocopy"
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.iphone_mtp = tk.BooleanVar(value=False)
        self.include_subfolders = tk.BooleanVar(value=True)
        self.restartable = tk.BooleanVar(value=False)
        self.preview_only = tk.BooleanVar(value=False)
        self.show_eta = tk.BooleanVar(value=True)
        self.threads = tk.IntVar(value=16)
        self.retries = tk.IntVar(value=3)
        self.wait_seconds = tk.IntVar(value=5)
        self.status = tk.StringVar(value="Pronto")

        self._build_interface()
        self._update_preview()
        self.root.after(100, self._process_events)

    def _build_interface(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(6, weight=1)

        ttk.Label(main, text="Copia file", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 14)
        )

        paths = ttk.LabelFrame(main, text="Cartelle", padding=12)
        paths.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        paths.columnconfigure(1, weight=1)

        ttk.Label(paths, text="Origine").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        source_entry = ttk.Entry(paths, textvariable=self.source)
        source_entry.grid(row=0, column=1, sticky="ew", pady=5)
        source_entry.bind("<KeyRelease>", self._on_path_change)
        ttk.Button(paths, text="Sfoglia...", command=self._browse_source).grid(
            row=0, column=2, padx=(8, 0), pady=5
        )

        ttk.Label(paths, text="Destinazione").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        destination_entry = ttk.Entry(paths, textvariable=self.destination)
        destination_entry.grid(row=1, column=1, sticky="ew", pady=5)
        destination_entry.bind("<KeyRelease>", self._on_path_change)
        ttk.Button(paths, text="Sfoglia...", command=self._browse_destination).grid(
            row=1, column=2, padx=(8, 0), pady=5
        )
        ttk.Checkbutton(
            paths,
            text="Origine iPhone collegato via USB (MTP, copia diretta)",
            variable=self.iphone_mtp,
            command=self._update_preview,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        options = ttk.LabelFrame(main, text="Opzioni di copia", padding=12)
        options.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        options.columnconfigure(3, weight=1)

        ttk.Checkbutton(
            options,
            text="Includi sottocartelle ( /S )",
            variable=self.include_subfolders,
            command=self._update_preview,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            options,
            text="Modalita' riavviabile ( /Z )",
            variable=self.restartable,
            command=self._update_preview,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            options,
            text="Solo simulazione ( /L )",
            variable=self.preview_only,
            command=self._update_preview,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            options,
            text="Mostra tempo stimato ( /ETA )",
            variable=self.show_eta,
            command=self._update_preview,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Label(options, text="Thread /MT").grid(row=0, column=2, sticky="e", padx=(18, 6), pady=3)
        thread_control = ttk.Spinbox(
            options, from_=1, to=128, textvariable=self.threads, width=7, command=self._update_preview
        )
        thread_control.grid(row=0, column=3, sticky="w", pady=3)
        thread_control.bind("<KeyRelease>", self._on_option_change)
        ttk.Label(options, text="Tentativi /R").grid(row=1, column=2, sticky="e", padx=(18, 6), pady=3)
        retry_control = ttk.Spinbox(
            options, from_=0, to=100, textvariable=self.retries, width=7, command=self._update_preview
        )
        retry_control.grid(row=1, column=3, sticky="w", pady=3)
        retry_control.bind("<KeyRelease>", self._on_option_change)
        ttk.Label(options, text="Attesa in secondi /W").grid(
            row=2, column=2, sticky="e", padx=(18, 6), pady=3
        )
        wait_control = ttk.Spinbox(
            options, from_=0, to=60, textvariable=self.wait_seconds, width=7, command=self._update_preview
        )
        wait_control.grid(row=2, column=3, sticky="w", pady=3)
        wait_control.bind("<KeyRelease>", self._on_option_change)

        ttk.Label(
            main,
            text=(
                "Nota iPhone: Robocopy richiede un percorso filesystem Windows. "
                "Per copiare direttamente, spunta l'opzione MTP e inserisci 'Questo PC\\Apple iPhone\\Internal Storage'. "
                "Sblocca l'iPhone e autorizza il computer."
            ),
            wraplength=770,
            justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(0, 12))

        preview = ttk.LabelFrame(main, text="Comando", padding=8)
        preview.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        preview.columnconfigure(0, weight=1)
        self.command_preview = tk.Text(preview, height=2, wrap="word", state="disabled")
        self.command_preview.grid(row=0, column=0, sticky="ew")

        output_frame = ttk.LabelFrame(main, text="Registro", padding=8)
        output_frame.grid(row=6, column=0, sticky="nsew", pady=(0, 12))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output = tk.Text(output_frame, wrap="word", state="disabled")
        self.output.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=scrollbar.set)

        controls = ttk.Frame(main)
        controls.grid(row=7, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        ttk.Label(controls, textvariable=self.status).grid(row=0, column=0, sticky="w")
        self.start_button = ttk.Button(controls, text="Avvia copia", command=self._start_copy)
        self.start_button.grid(row=0, column=1, padx=(8, 0))
        self.stop_button = ttk.Button(controls, text="Interrompi", command=self._stop_copy, state="disabled")
        self.stop_button.grid(row=0, column=2, padx=(8, 0))

    def _browse_source(self):
        path = filedialog.askdirectory(title="Seleziona la cartella di origine")
        if path:
            self.source.set(path)
            self._update_preview()

    def _browse_destination(self):
        path = filedialog.askdirectory(title="Seleziona la cartella di destinazione")
        if path:
            self.destination.set(path)
            self._update_preview()

    def _on_path_change(self, _event):
        self._update_preview()

    def _on_option_change(self, _event):
        self._update_preview()

    def _build_command(self):
        command = ["robocopy", self.source.get().strip(), self.destination.get().strip(), "*"]
        command.extend(["/S"] if self.include_subfolders.get() else [])
        command.extend(["/Z"] if self.restartable.get() else [])
        command.extend(["/MT:%d" % self.threads.get()])
        command.extend(["/R:%d" % self.retries.get(), "/W:%d" % self.wait_seconds.get()])
        command.extend(["/ETA"] if self.show_eta.get() else [])
        command.extend(["/L"] if self.preview_only.get() else [])
        return command

    def _update_preview(self):
        if self.iphone_mtp.get():
            rendered = "Copia diretta tramite Windows MTP: %s -> %s" % (
                self.source.get().strip() or "origine iPhone",
                self.destination.get().strip() or "destinazione",
            )
        else:
            try:
                command = self._build_command()
            except (tk.TclError, ValueError):
                command = ["robocopy", self.source.get().strip(), self.destination.get().strip(), "..."]
            rendered = subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)
        self.command_preview.configure(state="normal")
        self.command_preview.delete("1.0", "end")
        self.command_preview.insert("1.0", rendered)
        self.command_preview.configure(state="disabled")

    def _append_output(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _start_copy(self):
        if os.name != "nt":
            messagebox.showerror("Windows richiesto", "Robocopy e' disponibile solo su Windows.")
            return
        source = self.source.get().strip()
        destination = self.destination.get().strip()
        if not source or not destination:
            messagebox.showwarning("Percorsi mancanti", "Inserisci la cartella di origine e quella di destinazione.")
            return
        if os.path.normcase(os.path.normpath(source)) == os.path.normcase(os.path.normpath(destination)):
            messagebox.showwarning("Percorsi uguali", "Origine e destinazione non possono coincidere.")
            return
        if self.iphone_mtp.get():
            if self.preview_only.get():
                messagebox.showwarning(
                    "Simulazione non disponibile",
                    "La simulazione /L e' un'opzione Robocopy e non si applica alla copia MTP.",
                )
                return
            script_path = resource_path("iphone_mtp_copy.ps1")
            if not os.path.isfile(script_path):
                messagebox.showerror("Script non trovato", "Manca il file iphone_mtp_copy.ps1.")
                return
            command = [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                script_path,
                "-Source",
                source,
                "-Destination",
                destination,
            ]
            running_status = "Copia diretta iPhone via MTP..."
            self.active_mode = "mtp"
        else:
            try:
                command = self._build_command()
                if not 1 <= self.threads.get() <= 128 or self.retries.get() < 0 or self.wait_seconds.get() < 0:
                    raise ValueError
            except (tk.TclError, ValueError):
                messagebox.showwarning("Parametri non validi", "Controlla thread, tentativi e tempo di attesa.")
                return
            running_status = "Copia in corso..." if not self.preview_only.get() else "Simulazione in corso..."
            self.active_mode = "robocopy"

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=locale.getpreferredencoding(False),
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as error:
            self.process = None
            messagebox.showerror("Avvio non riuscito", "Impossibile avviare il processo di copia:\n%s" % error)
            return

        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
        self.status.set(running_status)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        threading.Thread(target=self._collect_output, args=(self.process,), daemon=True).start()

    def _collect_output(self, process):
        if process.stdout is not None:
            for line in process.stdout:
                self.events.put(("line", line))
        self.events.put(("done", process.wait()))

    def _process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "line":
                    self._append_output(value)
                else:
                    self.process = None
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    successful = value == 0 if self.active_mode == "mtp" else value < 8
                    if successful:
                        self.status.set("Completato (codice Robocopy %d)" % value)
                    else:
                        self.status.set("Errore (codice %s %d)" % ("MTP" if self.active_mode == "mtp" else "Robocopy", value))
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _stop_copy(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.status.set("Interruzione richiesta...")


if __name__ == "__main__":
    window = tk.Tk()
    RobocopyWindow(window)
    window.mainloop()