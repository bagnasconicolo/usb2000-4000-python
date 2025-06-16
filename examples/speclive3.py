# ui_spettro_ccd.py
"""
USB2000 live – grafico + “CCD strip”
Space = pausa/ripresa   (refresh 100 ms)
"""

import sys, time, numpy as np
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from seabreeze.spectrometers import Spectrometer
from seabreeze._exc import SeaBreezeError

# ---------- util ----------------------------------------------------------

def wavelength_to_rgb(l):
    """Restituisce (R,G,B)∈[0,1] per 200–1100 nm.
       Visibile: colore reale. UV/IR: falsi colori."""
    if l < 380:               # UV 200-380 → viola → blu
        t = (l - 200) / 180           # 0…1
        r, g, b = 0.5*(1-t), 0.0, 1.0
    elif l < 440:             # 380-440
        t = (l-380)/60;    r,g,b = 0, 0, 1
    elif l < 490:             # 440-490
        t = (l-440)/50;    r,g,b = 0, t, 1
    elif l < 510:             # 490-510
        t = (l-490)/20;    r,g,b = 0, 1, 1-t
    elif l < 580:             # 510-580
        t = (l-510)/70;    r,g,b = t, 1, 0
    elif l < 645:             # 580-645
        t = (l-580)/65;    r,g,b = 1, 1-t, 0
    elif l < 780:             # 645-780 rosso
        r,g,b = 1, 0, 0
    else:                     # IR 780-1100 → rosso → bianco
        t = (l-780)/320;      # 0…1
        r, g, b = 1, t, t
    return r, g, b

def boxcar(y, half=1):
    if half < 1:
        return y
    k = np.ones(2*half+1)/(2*half+1)
    return np.convolve(y, k, 'same')

# ---------- UI ------------------------------------------------------------

class LiveSpectrum(QtWidgets.QMainWindow):
    REFRESH_MS = 100      # 10 Hz

    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB2000 – spettro + CCD (SPACE = pausa)")
        self.resize(900, 600)

        # ----- layout con 2 righe ----------------------------------------
        glw = pg.GraphicsLayoutWidget()
        self.setCentralWidget(glw)
        self.plot = glw.addPlot(row=0, col=0)
        self.plot.setLabel('bottom', "Lunghezza d'onda (nm)")
        self.plot.setLabel('left', "Conteggi")
        self.curve = self.plot.plot(pen=pg.mkPen(width=2))

        self.img_vb = glw.addViewBox(row=1, col=0, enableMenu=False)
        self.img_vb.setMaximumHeight(60)
        self.img_vb.setMouseEnabled(x=False, y=False)
        self.img_item = pg.ImageItem(axisOrder='row-major')
        self.img_vb.addItem(self.img_item)
        self.img_vb.setAspectLocked(False)

        # ----- spettrometro ----------------------------------------------
        try:
            self.spec = Spectrometer.from_first_available()
        except SeaBreezeError as e:
            QtWidgets.QMessageBox.critical(self, "Errore", str(e))
            sys.exit(1)

        self.integ_ms  = 10
        self.spec.integration_time_micros(self.integ_ms*1000)
        self.wl = self.spec.wavelengths()
        self.base_rgb = np.array([wavelength_to_rgb(w) for w in self.wl])

        # ----- timer & hot-key -------------------------------------------
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(self.REFRESH_MS)
        self.running = True
        QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self, activated=self.toggle)

    # -------------------------------------------------------------------
    def update_frame(self):
        try:
            counts = self.spec.intensities(correct_dark_counts=True)
        except Exception as e:
            print("Errore lettura:", e)
            return

        counts = boxcar(counts, 1)
        norm = counts / counts.max() if counts.max() else counts
        self.curve.setData(self.wl, counts)

        # --- costruisci RGB dell’immagine “CCD” -------------------------
        rgb_line = (self.base_rgb * norm[:, None]).clip(0, 1)
        rgb_u8 = (rgb_line * 255).astype(np.uint8)
        img = np.tile(rgb_u8[None, :, :], (50, 1, 1))   # altezza 50 px

        # mostra immagine; larghezza = range spettrale
        self.img_item.setImage(img, autoLevels=False)
        self.img_item.resetTransform()
        self.img_item.setRect(QtCore.QRectF(self.wl[0], 0, self.wl[-1]-self.wl[0], 1))
        self.img_vb.setYRange(0, 1, padding=0)
        self.img_vb.setXRange(self.wl[0], self.wl[-1], padding=0)

    # -------------------------------------------------------------------
    def toggle(self):
        if self.running:
            self.timer.stop();  self.statusBar().showMessage("⏸ Pausa", 2000)
        else:
            self.timer.start(self.REFRESH_MS);  self.statusBar().showMessage("▶️  Live", 2000)
        self.running = not self.running

    # -------------------------------------------------------------------
    def closeEvent(self, ev):
        try: self.spec.close()
        except Exception: pass
        ev.accept()

# -------------------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = LiveSpectrum();  win.show()
    sys.exit(app.exec())