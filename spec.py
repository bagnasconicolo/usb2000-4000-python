"""
Acquisizione spettro Ocean Optics USB2000 (macOS / Linux / Windows)
Requisiti:
    pip install seabreeze numpy matplotlib
    # macOS: esegui da terminale con 'sudo python acquisisci_usb2000.py'
"""

import sys, time
import numpy as np
import matplotlib.pyplot as plt
from seabreeze.spectrometers import Spectrometer
from seabreeze._exc import SeaBreezeError           # gestione errori

# ---------- funzioni utili --------------------------------------------------

def boxcar_smooth(y: np.ndarray, half_width: int) -> np.ndarray:
    """Lisce con una finestra di larghezza (2*half_width+1)."""
    if half_width < 1:
        return y
    kernel = np.ones(2*half_width + 1, dtype=float) / (2*half_width + 1)
    return np.convolve(y, kernel, mode="same")

# ---------- script principale ----------------------------------------------

def main():
    try:
        spec = Spectrometer.from_first_available()
    except SeaBreezeError as e:
        sys.exit(f"Errore: nessuno spettrometro trovato ({e}).")

    print(f"Trovato: {spec.model}  S/N: {spec.serial_number}")

    # Parametri di acquisizione
    integ_ms = 100            # integrazione singola in millisecondi
    n_average = 5             # spettri da mediare
    dark_correct = True       # sottrae i dark counts
    boxcar_px = 2             # lisciatura boxcar (pixel per lato)

    spec.integration_time_micros(integ_ms * 1000)  # libreria vuole µs
    wl = spec.wavelengths()                         # array 4096-px

    # Acquisizione + media
    spec_sum = np.zeros_like(wl, dtype=float)
    print(f"Acquisisco {n_average} spettri da {integ_ms} ms…")
    for i in range(n_average):
        counts = spec.intensities(correct_dark_counts=dark_correct)
        counts = boxcar_smooth(counts, boxcar_px)
        spec_sum += counts
        time.sleep(integ_ms / 1000)

    spectrum = spec_sum / n_average
    spec.close()   # buona abitudine

    # Salva e visualizza
    out = np.column_stack([wl, spectrum])
    np.savetxt("usb2000_spectrum.tsv", out,
               header="wavelength_nm\tintensity_counts")

    plt.plot(wl, spectrum)
    plt.xlabel("Lunghezza d'onda (nm)")
    plt.ylabel("Conteggi")
    plt.title("USB2000 – spettro medio")
    plt.tight_layout()
    plt.show()

    print("Salvato in usb2000_spectrum.tsv")

if __name__ == "__main__":
    main()