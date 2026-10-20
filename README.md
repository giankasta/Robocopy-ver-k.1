# Robocopy-ver-k.1

Una piccola interfaccia grafica per usare Robocopy, gia' incluso in Windows, e copiare grandi quantita' di file.

## Avvio da Python

Con Python 3 installato su Windows, esegui dalla cartella del progetto:

```powershell
py robocopy_gui.py
```

## Creazione dell'eseguibile Windows

Su Windows, fai doppio clic su `build_windows.bat` oppure eseguilo dal prompt. Lo script installa PyInstaller se necessario e crea `dist\CopiaFotoIPhone.exe`, una finestra senza console che include anche il supporto MTP. La compilazione va eseguita su Windows: PyInstaller non crea eseguibili Windows da Linux. Per usare l'app su un altro PC, trasferisci l'eseguibile generato; per la copia MTP quel PC deve avere i driver Apple e Windows deve riconoscere l'iPhone.

Inserisci o seleziona la cartella di origine e quella di destinazione. I valori iniziali Robocopy seguono il comando richiesto: `* /S /R:3 /W:5 /MT:16 /ETA`. Puoi modificare sottocartelle, modalita' riavviabile, thread, tentativi, attesa e visualizzazione del tempo stimato. L'opzione "Solo simulazione" aggiunge `/L` e mostra cosa verrebbe copiato senza copiare i file.

La GUI non usa `/MIR` o `/PURGE`: i file gia' presenti nella destinazione non vengono eliminati. I codici Robocopy da 0 a 7 indicano un'esecuzione senza errori fatali; da 8 in su indicano errori.

## iPhone collegato via USB

Sblocca l'iPhone, conferma "Autorizza questo computer" e inserisci come origine `Questo PC\Apple iPhone\Internal Storage`. Seleziona "Origine iPhone collegato via USB (MTP, copia diretta)" per trasferire i file direttamente dal dispositivo alla destinazione scelta, senza una cartella intermedia. Questa modalita' usa Windows Shell/MTP, non Robocopy; le opzioni `/MT`, `/R`, `/W` e `/ETA` si applicano solo alle normali cartelle filesystem. Il trasferimento MTP dipende dal supporto del dispositivo e dai driver Apple installati in Windows.
