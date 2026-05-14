import sys
sys.path.append('parser')

import unittest
from unittest.mock import patch, MagicMock

import database.db as db
import processor.downloader

class TestParserLogic(unittest.TestCase):
    @patch('processor.downloader.is_tender_in_db')
    @patch('processor.downloader.get_link_to_file_page')
    @patch('processor.downloader.get_all_from_processing_queue')
    def test_download_tenders_files_skips_processed(self, mock_get_all, mock_get_link, mock_is_tender_in_db):
        mock_get_all.return_value = [
            {'tender_number': '0311234', 'url': 'http://test', 'law': '44-ФЗ', 'files_downloaded': False}
        ]
        mock_is_tender_in_db.return_value = True

        processor.downloader.download_tenders_files()

        mock_get_link.assert_not_called()

if __name__ == '__main__':
    unittest.main()
