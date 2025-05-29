# ui_spettro.py
"""
UI live per Ocean Optics USB2000
Acquisisce e aggiorna lo spettro ogni 1 s.

Avvia con:
    python ui_spettro.py
"""

import sys, time, numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
from seabreeze.spectrometers import Spectrometer
from seabreeze._exc import SeaBreezeError

# -------- helper ----------------------------------------------------------

def boxcar(y: np.ndarray, half: int = 2) -> np.ndarray:
    """Lisciatura boxcar di larghezza 2*half+1."""
    if half < 1:
        return y
    k = np.ones(2 * half + 1) / (2 * half + 1)
    return np.convolve(y, k, mode="same")

# -------- Qt application --------------------------------------------------

class LiveSpectrum(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB2000 – spettro live (1 s)")
        self.resize(900, 500)

        # grafico
        self.plot = pg.PlotWidget(axisItems={'bottom': pg.AxisItem(orientation='bottom')})
        self.setCentralWidget(self.plot)
        self.curve = self.plot.plot(pen=pg.mkPen(width=2))

        # connessione spettrometro
        try:
            self.spec = Spectrometer.from_first_available()
        except SeaBreezeError as e:
            QtWidgets.QMessageBox.critical(self, "Errore", f"Nessuno spettrometro trovato:\n{e}")
            sys.exit(1)

        print(f"Trovato: {self.spec.model}  S/N: {self.spec.serial_number}")

        # parametri acquisizione
        self.integ_ms = 100          # integrazione singola
        self.n_avg    = 3            # medie
        self.boxcar_px = 2           # lisciatura
        self.spec.integration_time_micros(self.integ_ms * 1000)
        self.wl = self.spec.wavelengths()

        # set up timer 1 s
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.acquire_and_plot)
        self.timer.start(1000)

    # ---------------------------------------------------------------------
    def acquire_and_plot(self):
        """Legge n_avg spettri e aggiorna la curva."""
        try:
            s = np.zeros_like(self.wl, dtype=float)
            for _ in range(self.n_avg):
                s += self.spec.intensities(correct_dark_counts=True)
                time.sleep(self.integ_ms / 1000)
            s /= self.n_avg
            s = boxcar(s, self.boxcar_px)
        except Exception as e:
            print("Errore durante lettura spettro:", e)
            return

        self.curve.setData(self.wl, s)
        self.plot.setLabel('bottom', "Lunghezza d'onda (nm)")
        self.plot.setLabel('left', "Conteggi")
        self.plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)

    # ---------------------------------------------------------------------
    def closeEvent(self, ev):
        """Chiude in modo pulito lo spettrometro."""
        try:
            self.spec.close()
        except Exception:
            pass
        ev.accept()

# --------------------------------------------------------------------------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = LiveSpectrum()
    win.show()
    sys.exit(app.exec())