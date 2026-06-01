# WZSplitter

Splits multi-WZ PDF files into individual PDFs per WZ number using OCR.

Each page is scanned for a WZ number in the top-right corner. Pages sharing the same WZ number are grouped and saved as a single PDF file.

## Requirements

### Python dependencies

```bash
pip install -r requirements.txt
```

### External tools

- **Tesseract OCR 5.x** — [Windows installer (UB-Mannheim)](https://github.com/UB-Mannheim/tesseract/wiki)  
  Make sure the `eng` language pack is selected during installation.
- **Poppler** — [Windows binaries](https://github.com/oschwartz10612/poppler-windows/releases)

## Configuration

Copy `.env.example` to `.env` and fill in the paths:

```
WZ_TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
WZ_POPPLER_PATH=C:\path\to\poppler\bin
```

On Linux the paths typically are:
```
WZ_TESSERACT_PATH=/usr/bin/tesseract
WZ_POPPLER_PATH=/usr/bin
```

## Usage

**Process a single file:**
```bash
python main.py --path path/to/file.pdf --output path/to/output/
```

**Process all PDFs in a directory:**
```bash
python main.py --path path/to/dir/ --output path/to/output/
```

The `--output` argument is optional. If omitted, output files are saved next to the source PDF.

### Example output

```
20250527_080209.pdf:
  [01] WZ-105_26_DINO_05.pdf  (3 page[s])
  [02] WZ-439_26_JER_05.pdf  (1 page[s])
  [03] WZ-143_26_KAUF_05.pdf  (2 page[s])
  ...

Total: 13 WZ's from 20250527_080209.pdf.
Moved 20250527_080209.pdf to ./input/01-06-2026/20250527_080209.pdf.
```

After processing, the source PDF is moved to a dated subdirectory (`DD-MM-YYYY/`) next to its original location.

## Download (Windows .exe)

A prebuilt Windows executable is available on the [Releases](../../releases/latest) page — no Python installation required.

The `.exe` still requires Tesseract and Poppler to be installed separately (see [Requirements](#requirements)), and a `.env` file placed in the same directory as the executable.
