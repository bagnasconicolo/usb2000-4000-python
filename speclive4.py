# ui_spettro_ccd_v4.py
"""
USB2000 live – grafico, CCD strip, hot‑keys:
 SPACE → pausa / riprendi
 C     → salva CSV                (usb2000_YYYYMMDD_HHMMSS.csv)
 P     → salva PNG plot + CCD     (usb2000_YYYYMMDD_HHMMSS_plot.png + _ccd.png)
 S     → salva CSV+PNG in cartella (toolbar o scorciatoia)
 Hover → cursore λ, I nella status‑bar
"""

import sys, time, numpy as np, datetime as dt, os
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter
from seabreeze.spectrometers import Spectrometer
from seabreeze._exc import SeaBreezeError

# --------------------- util ------------------------------------------------
def wavelength_to_rgb(l):
    if l < 380: t=(l-200)/180; return 0.5*(1-t),0,1
    if l < 440: return 0,0,1
    if l < 490: t=(l-440)/50;return 0,t,1
    if l < 510: t=(l-490)/20;return 0,1,1-t
    if l < 580: t=(l-510)/70;return t,1,0
    if l < 645: t=(l-580)/65;return 1,1-t,0
    if l < 780: return 1,0,0
    t=(l-780)/320; return 1,t,t                         # IR
def boxcar(y, half=1):
    if half<1: return y
    k=np.ones(2*half+1)/(2*half+1)
    return np.convolve(y,k,'same')
def timestamp():
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")

# --------------------- UI --------------------------------------------------
class LiveSpectrum(QtWidgets.QMainWindow):
    REFRESH_MS = 100
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB2000 – spettro live  [SPACE pausa | C csv | P plot+ccd | S cartella]")
        self.resize(900,600)

        # layout: grafico + immagine
        glw = pg.GraphicsLayoutWidget(); self.setCentralWidget(glw)
        self.glw = glw  # serve per l'export completo
        self.plot = glw.addPlot(row=0,col=0)
        self.plot.setLabel('bottom',"Lunghezza d'onda (nm)")
        self.plot.setLabel('left',"Conteggi")
        self.curve = self.plot.plot(pen=pg.mkPen(width=2))
        # ---------- cross‑hair cursor ----------------------------------
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y'))
        self.hLine = pg.InfiniteLine(angle=0,  movable=False, pen=pg.mkPen('y'))
        self.plot.addItem(self.vLine); self.plot.addItem(self.hLine)
        # aggiorna le linee al movimento del mouse (60 Hz max)
        self._proxy = pg.SignalProxy(self.plot.scene().sigMouseMoved,
                                     rateLimit=60,
                                     slot=self._mouse_moved)
        self.img_vb = glw.addViewBox(row=1,col=0,enableMenu=False)
        self.img_vb.setMaximumHeight(60); self.img_vb.setMouseEnabled(x=False,y=False)
        self.img_item = pg.ImageItem(axisOrder='row-major'); self.img_vb.addItem(self.img_item)

        # spettrometro
        try:
            self.spec = Spectrometer.from_first_available()
        except SeaBreezeError as e:
            QtWidgets.QMessageBox.critical(self,"Errore",str(e)); sys.exit(1)
        self.integ_ms=10; self.spec.integration_time_micros(self.integ_ms*1000)
        self.wl = self.spec.wavelengths()
        # mostra nome e seriale sul titolo del plot
        self.plot.setTitle(f"{self.spec.model}  S/N: {self.spec.serial_number}")
        self.base_rgb = np.array([wavelength_to_rgb(w) for w in self.wl])
        self.last_counts = None                          # buffer per salvataggio

        # timer & scorciatoie
        self.timer = QtCore.QTimer(self); self.timer.timeout.connect(self.update_frame)
        self.timer.start(self.REFRESH_MS); self.running=True
        QtWidgets.QShortcut(QtGui.QKeySequence("Space"), self, activated=self.toggle)
        QtWidgets.QShortcut(QtGui.QKeySequence("C"),     self, activated=self.save_csv)
        QtWidgets.QShortcut(QtGui.QKeySequence("P"),     self, activated=self.save_png)
        # toolbar e azione di salvataggio combinato
        self.toolbar = self.addToolBar("File")
        act_save = QtGui.QAction("Save CSV+PNG", self)
        act_save.setShortcut("S")
        act_save.triggered.connect(self.save_all)
        self.toolbar.addAction(act_save)

    # ------------- aggiornamento ------------------------------------------
    def update_frame(self):
        try:
            counts = self.spec.intensities(correct_dark_counts=True)
        except Exception as e:
            print("Errore lettura:",e); return
        counts = boxcar(counts,1); self.last_counts = counts
        self.curve.setData(self.wl, counts)
        norm = counts/counts.max() if counts.max() else counts
        rgb_line = (self.base_rgb*norm[:,None]).clip(0,1)
        img = np.tile((rgb_line*255).astype(np.uint8)[None,:,:],(50,1,1))
        self.img_item.setImage(img,autoLevels=False); self.img_item.resetTransform()
        self.img_item.setRect(QtCore.QRectF(self.wl[0],0,self.wl[-1]-self.wl[0],1))
        self.img_vb.setYRange(0,1,padding=0); self.img_vb.setXRange(self.wl[0],self.wl[-1],padding=0)

    # ------------------- cursore -----------------------------------
    def _mouse_moved(self, evt):
        """
        Aggiorna la posizione del cursore e mostra λ & I sulla status‑bar.
        """
        pos = evt[0]  # QPointF dal SignalProxy
        if self.plot.sceneBoundingRect().contains(pos):
            mouse_point = self.plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            self.statusBar().showMessage(f"λ = {x:0.1f} nm   I = {y:0.0f}", 0)

    # ------------- hotkeys -------------------------------------------------
    def toggle(self):
        if self.running: self.timer.stop(); self.statusBar().showMessage("⏸ Pausa",2000)
        else: self.timer.start(self.REFRESH_MS); self.statusBar().showMessage("▶️ Live",2000)
        self.running = not self.running

    def save_csv(self, filepath=None):
        if self.last_counts is None: return
        fname = filepath or f"usb2000_{timestamp()}.csv"
        np.savetxt(fname, np.column_stack([self.wl, self.last_counts]),
                   delimiter=",", header="wavelength_nm,intensity_counts", comments='')
        self.statusBar().showMessage(f"💾 CSV salvato: {fname}",3000)

    def save_png(self, filepath=None):
        """
        Salva il grafico e la strip CCD come PNG separati.
        """
        base = filepath or f"usb2000_{timestamp()}"
        # salva grafico
        exporter_plot = ImageExporter(self.plot)
        exporter_plot.params['width'] = 1200
        exporter_plot.export(f"{base}_plot.png")
        # salva ccd strip
        exporter_ccd = ImageExporter(self.img_item)
        exporter_ccd.params['width'] = 1200
        exporter_ccd.export(f"{base}_ccd.png")
        self.statusBar().showMessage(f"🖼️  Salvati {base}_plot.png e {base}_ccd.png", 4000)

    def save_all(self):
        """
        Crea una cartella con timestamp, salva sia CSV che PNG al suo interno.
        """
        base = f"usb2000_{timestamp()}"
        os.makedirs(base, exist_ok=True)
        self.save_csv(os.path.join(base, base + ".csv"))
        self.save_png(os.path.join(base, base))
        self.statusBar().showMessage(f"✅ Salvati CSV e PNG in {base}/", 4000)

    # ----------------------------------------------------------------------
    def closeEvent(self,ev):
        try: self.spec.close()
        except Exception: pass
        ev.accept()

# --------------------------------------------------------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv); win=LiveSpectrum(); win.show(); sys.exit(app.exec())
