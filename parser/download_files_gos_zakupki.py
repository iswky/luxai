from bs4 import BeautifulSoup
from bs4 import Tag
from urllib.parse import urljoin
from typing import List, Dict, Optional, Tuple, Any
import requests
import os

from db import get_all_from_processing_queue, update_processing_queue_field

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://zakupki.gov.ru/',
    'Connection': 'keep-alive',
}


# safe archive unpacking with all error handling
def unarchive_file(file_path: str):

    import shutil
    from unzipall import extract
    from unzipall.exceptions import ArchiveExtractionError

    
    # checking file existence
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    
    # checking that it is a file and not a folder
    if not os.path.isfile(file_path):
        print(f"Path is not a file: {file_path}")
        return False
    
    try:
        # we are trying to unpack the archive
        print(f"Unpacking: {file_path}")
        extract(file_path)
        
        # deleting the archive after successful unpacking
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Archive deleted: {file_path}")
        
    except ArchiveExtractionError as e:
        print(f"Unpack error {file_path}: {e}")
        # don't delete the archive so you can try later
        return False
    except Exception as e:
        print(f"Unexpected error unpacking {file_path}: {e}")
        return False
    
    # forming paths for moving files
    try:
        # getting the name without extension (more reliable way)
        source_folder = os.path.splitext(file_path)[0]
        
        # if the folder does not exist, the archive may not have created the folder
        if not os.path.exists(source_folder):
            print(f"Folder {source_folder} not found after unpacking")
            return False
        
        # parent folder (one level up)
        destination_folder = os.path.dirname(source_folder)
        
        print(f"Source folder: {source_folder}")
        print(f"Destination folder: {destination_folder}")
        
        # moving all files and folders
        moved_count = 0
        error_count = 0
        
        for item in os.listdir(source_folder):
            source_path = os.path.join(source_folder, item)
            destination_path = os.path.join(destination_folder, item)
            
            try:
                # if there is already such a file/folder in the destination folder
                if os.path.exists(destination_path):
                    # generating a unique name
                    base, ext = os.path.splitext(item)
                    counter = 1
                    while os.path.exists(destination_path):
                        new_name = f"{base}_{counter}{ext}"
                        destination_path = os.path.join(destination_folder, new_name)
                        counter += 1
                    print(f"Renamed: {item} -> {os.path.basename(destination_path)}")
                
                # moving
                shutil.move(source_path, destination_path)
                moved_count += 1
                
            except Exception as e:
                print(f"Error moving {item}: {e}")
                error_count += 1
                continue
        
        # deleting the original folder
        try:
            if os.path.exists(source_folder):
                os.rmdir(source_folder)  # trying to delete an empty folder
                print(f"Deleted folder: {source_folder}")
        except OSError:
            # the folder is not empty, delete it recursively
            try:
                shutil.rmtree(source_folder)
                print(f"Deleted folder with content: {source_folder}")
            except Exception as e:
                print(f"Could not delete folder {source_folder}: {e}")
        
        print(f"Moved files: {moved_count}, errors: {error_count}")
        return True
        
    except Exception as e:
        print(f"Error processing unpacked files: {e}")
        return False

def download_file(url: str, filename: str = "file.html", tender_number: str = "unknown_tender/"):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }

    # form the path: tenders_files/<tender_number>/
    path = os.path.join("tenders_files", tender_number)
    os.makedirs(path, exist_ok=True)
    filepath = os.path.join(path, filename)

    try:
        r = requests.get(url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        if os.path.splitext(filepath)[1].lower() in ['.zip', '.rar', '.7z', '.tar']:
            unarchive_file(filepath)


        print('File', filename, 'downloaded successfully')

        return filepath
        
    except requests.RequestException as e:
        print(f"Error downloading {filename}: {e}")
        raise

def extract_file_links_44FZ(html_content: str, base_url: str = 'https://zakupki.gov.ru') -> List[Dict[str, Optional[str]]]:
    
    soup: BeautifulSoup = BeautifulSoup(html_content, 'html.parser')
    files: List[Dict[str, Optional[str]]] = []

    section: List = soup.find('div', class_= "blockFilesTabDocs")

    if not section:
        print("Section blockFilesTabDocs not found")
        return []
    
    attachments: List = section.find_all('div', class_="attachment row")
    print(f"Found attachments: {len(attachments)}")

    for i, attachment in enumerate(attachments, 1):
        link: Optional[Tag] = attachment.find('a', href=lambda h: h and 'https://zakupki.gov.ru' in h)

        if link:
            file_url: str = link.get('href', '')
            file_title: str = link.get('title', '')
            file_name: str = link.text.strip()

            print(file_url)
            print(file_title)
            print('\n')
            
            file_info = {
                'url': file_url,
                'title': file_title
            }

            files.append(file_info)

    return files

def extract_file_links_223FZ(url: str, base_url: str = 'https://zakupki.gov.ru') -> List[Dict[str, Optional[str]]]:

    from playwright.sync_api import sync_playwright

    try:

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url)

            # ✅ we are waiting inside the block
            try:
                page.wait_for_selector("a[href*='download.html']", timeout=15000)
                html = page.content()
                browser.close()
                # continue processing html
            except Exception:
                print(f"Timeout: element 'a[href*='download.html']' not found on {url}")
                browser.close()
                return []

        # ✅ we use the html that we received
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')
        files: List[Dict[str, Optional[str]]] = []

        section: Tag = soup.find('section', class_="card-attachments")

        if not section:
            print("Section \"card-attachments\" not found")
            return []

        counts = section.find_all('span', class_=lambda x: x and 'count' in x.split())

        if not counts:
            print("Sections \"count \" not found")
            return []

        for count in counts:
            link = count.find('a', string=lambda text: text and 'download.html')

            if link:

                from html import unescape

                file_url = "https://zakupki.gov.ru" + link.get('href')
                file_name: str = link.text.strip()

                tooltip = link.get('data-tooltip')
                tooltip_decoded = unescape(tooltip)
                file_name = BeautifulSoup(tooltip_decoded, 'html.parser').find('span', class_='custom-tooltiptext').text

                print(file_url)
                print(file_name)
                print('\n')
                
                file_info = {
                    'url': file_url,
                    'title': file_name
                }

                files.append(file_info)
            else:
                print("filelink not found")

        return files
    
    except Exception as e:
        print(f"Error loading {url}: {e}")
        return []

def get_link_to_file_page(tender_link: str, FZ: str) -> str:

    response = requests.get(tender_link, headers = headers)

    soup: BeautifulSoup = BeautifulSoup(response.text, 'html.parser')

    if FZ == "44-ФЗ":
        section = soup.find('div', class_= "tabsNav d-flex align-items-end")
    elif FZ == "223-ФЗ":
        section = soup.find('div', class_= "tabsNav d-flex")
    else:
        return ""

    if not section:
        print("Section tabsNav d-flex not found")
        return ""

    link: Optional[Tag] = section.find('a', href=lambda h: h and 'documents.html' in h)

    if link:
        docs_page_url: str = link.get('href', '')

        print(docs_page_url)
        print('\n')

        return docs_page_url

    return ""

def download_tenders_files():
    tenders = get_all_from_processing_queue()

    for tender in tenders:
        full_tender_num = tender['tender_number']
        tender_id = full_tender_num[2:] if len(full_tender_num) > 2 else full_tender_num
        tender_link = tender['url']
        FZ = tender['law']
        files_downloaded = tender['files_downloaded']

        if files_downloaded:
            continue

        file_page_link = get_link_to_file_page(tender_link, FZ)
        if not file_page_link:
            continue

        url: str = "https://zakupki.gov.ru" + file_page_link

        print()

        print(url)
        print(f"Downloading from site: {url}")
        print(f"Downloading files for tender: {tender_id}")

        files: List[Dict[str, Optional[str]]] = []
        if FZ == "44-ФЗ":
            # getting html
            try:
                response = requests.get(url, headers = headers, timeout=15)
                html_text: str = response.text
                files = extract_file_links_44FZ(html_text)
            except Exception as e:
                print(f"Error fetching 44-FZ links: {e}")
                continue
        elif FZ == "223-ФЗ":
            files = extract_file_links_223FZ(url)
        else:
            continue

        if not files:
            continue

        try:
            for file_info in files:
                download_file(file_info['url'], file_info['title'], tender_id)

            update_processing_queue_field(full_tender_num, 'files_downloaded', True)
            print(f"Marked {full_tender_num} as downloaded")
            
        except requests.RequestException as e:
            print(f"Error downloading files for {tender_id}: {e}")


if __name__ == "__main__":

    print(get_link_to_file_page("https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=0320100018726000131", "44-ФЗ"))
    # download_tenders_files()