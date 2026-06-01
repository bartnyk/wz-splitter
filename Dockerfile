# Używamy Debiana jako bazy
FROM debian:bullseye-slim

# Instalacja Wine i wget
RUN dpkg --add-architecture i386 && apt-get update && \
    apt-get install -y wine wine32 wine64 wget ca-certificates && \
    apt-get clean

# Pobieranie i instalacja Windowsowego Pythona (3.10) wewnątrz Wine
RUN wget https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe && \
    wine python-3.10.0-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 && \
    rm python-3.10.0-amd64.exe

# Ustawienie zmiennych środowiskowych, aby Wine wiedziało gdzie jest Python
ENV WINEPREFIX=/root/.wine
WORKDIR /src

# Komenda instalująca zależności i budująca EXE
ENTRYPOINT ["sh", "-c", "wine pip install --upgrade pip && wine pip install -r requirements.txt && wine pyinstaller --onefile --clean $0"]