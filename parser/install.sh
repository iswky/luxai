#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Начало установки зависимостей${NC}"
echo -e "${GREEN}================================${NC}"

# Обновление pip
echo -e "${YELLOW}Обновление pip...${NC}"
pip install --upgrade pip

# Основные библиотеки
echo -e "${YELLOW}Установка основных библиотек...${NC}"
pip install requests
pip install beautifulsoup4
pip install lxml

# Работа с Excel
echo -e "${YELLOW}Установка библиотек для работы с Excel...${NC}"
pip install openpyxl

# Работа с PDF и документами
echo -e "${YELLOW}Установка библиотек для работы с документами...${NC}"
pip install pypdf
pip install python-docx
pip install docx2pdf

# Работа с данными и конвертацией
echo -e "${YELLOW}Установка библиотек для обработки данных...${NC}"
pip install pandas
pip install matplotlib

# Работа с архивами
echo -e "${YELLOW}Установка библиотек для работы с архивами...${NC}"
pip install unzipall

# Автоматизация браузера
echo -e "${YELLOW}Установка Playwright...${NC}"
pip install playwright
echo -e "${YELLOW}Установка браузера для Playwright...${NC}"
playwright install chromium