from scraper.zakupki_scraper import Parse_gos_zakupki
from scraper.city_scraper import city_parse, tender_city_parse
from processor.downloader import download_tenders_files, download_1tender_files
from processor.file_filter import file_filter, file_parser, filter_single_tender_files, parse_single_tender_files
from processor.validator import tender_validator
from database.db import deduplicate_tenders_in_db, get_all_from_processing_queue
from typing import List
import os
 
# description: function process_queue. args: . returns: any.
def process_queue():
    print("Processing queue...")

    tenders = get_all_from_processing_queue()

    for tender in tenders:
        tender_city_parse(tender)
        download_1tender_files(tender)
        deduplicate_tenders_in_db()
        filter_single_tender_files(tender)
        parse_single_tender_files(tender)

    print("Queue processed.")

def process_new_tenders(tenders: List[dict]):
    print("Processing new tenders...")

    for tender in tenders:
        tender_city_parse(tender)
        download_1tender_files(tender)
        deduplicate_tenders_in_db()
        filter_single_tender_files(tender)
        parse_single_tender_files(tender)
        
    print("New tenders processed.")

# description: function main. args: . returns: any.
def main():
    interactive = os.getenv("INTERACTIVE_MODE", "true").lower() == "true"

    tender_validator()

    # # Process the queue initially to clear any backlog
    process_queue()

    # Run the parser and pass the callback to process after each page
    Parse_gos_zakupki(interactive=interactive, page_callback=process_new_tenders)
 
if __name__ == "__main__":
    # Parse_gos_zakupki(interactive=True)


    main()
