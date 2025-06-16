# ui_spettro_fast.py
"""
Spettro live USB2000 – refresh 100 ms, toggle con SPACE.
Dipendenze: PySide6, pyqtgraph, seabreeze, numpy
"""

import sys, time, numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from seabreeze.spectrometers import Spectrometer
from seabreeze._exc import SeaBreezeError

# ----------------- utility -------------------------------------------------
def boxcar(arr: np.ndarray, half: int = 2) -> np.ndarray:
    if half < 1:
        return arr
    k = np.ones(2 * half + 1) / (2 * half + 1)
    return np.convolve(arr, k, mode="same")

# ----------------- finestra principale ------------------------------------
class LiveSpectrum(QtWidgets.QMainWindow):
    REFRESH_MS = 100          # <- frequenza campionamento (100 ms = 10 Hz)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB2000 – spettro live (SPACE = start/stop)")
        self.resize(900, 500)

        # ---------- grafico
        self.plot = pg.PlotWidget()
        self.setCentralWidget(self.plot)
        self.curve = self.plot.plot(pen=pg.mkPen(width=2))

        # ---------- spettrometro
        try:
            self.spec = Spectrometer.from_first_available()
        except SeaBreezeError as e:
            QtWidgets.QMessageBox.critical(self, "Errore", f"Nessuno spettrometro trovato:\n{e}")
            sys.exit(1)

        self.integ_ms   = 10       # integrazione breve, così entra nel ciclo 100 ms
        self.n_avg      = 1        # niente media per massima velocità
        self.boxcar_px  = 1
        self.spec.integration_time_micros(self.integ_ms * 1000)
        self.wl = self.spec.wavelengths()

        # ---------- timer & stato
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.acquire_and_plot)
        self.timer.start(self.REFRESH_MS)
        self.running = True

        # ---------- scorciatoia SPACE per toggle
        QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self, activated=self.toggle)

    # ---------------------------------------------------------------------
    def acquire_and_plot(self):
        try:
            counts = self.spec.intensities(correct_dark_counts=True)
            counts = boxcar(counts, self.boxcar_px)
            self.curve.setData(self.wl, counts)
        except Exception as e:
            # salta un frame se c’è un errore momentaneo
            print("Errore lettura:", e)

    # ---------------------------------------------------------------------
    def toggle(self):
        """Pausa/riavvia acquisizione (SPACE)."""
        if self.running:
            self.timer.stop()
            self.statusBar().showMessage("⏸ Pausa", 2000)
        else:
            self.timer.start(self.REFRESH_MS)
            self.statusBar().showMessage("▶️  In acquisizione", 2000)
        self.running = not self.running

    # ---------------------------------------------------------------------
    def closeEvent(self, ev):
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