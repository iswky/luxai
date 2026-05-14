from zakupki_parser import Parse_gos_zakupki
from city_parse import city_parse
from download_files_gos_zakupki import download_tenders_files
from file_filter import file_filter, file_parser
from tender_validator import tender_validator, deduplicate_tenders_in_excel
from db import deduplicate_tenders_in_db
import os
 
def process_queue():
    print("Processing queue...")
    city_parse()
    download_tenders_files()
    deduplicate_tenders_in_db()
    file_filter()
    file_parser()
    print("Queue processed.")

def main():
    interactive = os.getenv("INTERACTIVE_MODE", "true").lower() == "true"

    tender_validator()

    # Process the queue initially to clear any backlog
    process_queue()

    # Run the parser and pass the callback to process after each page
    Parse_gos_zakupki(interactive=interactive, page_callback=process_queue)
 
if __name__ == "__main__":
    main()
