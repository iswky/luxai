from zakupki_parser import Parse_gos_zakupki
from city_parse import city_parse
from download_files_gos_zakupki import download_tenders_files
from file_filter import file_filter

def main():
    Parse_gos_zakupki()
    city_parse()
    download_tenders_files()
    file_filter()

if __name__ == "__main__":
    main()