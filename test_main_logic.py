import sys
sys.path.append('parser')

import unittest
from unittest.mock import patch, MagicMock

import db
import download_files_gos_zakupki

class TestParserLogic(unittest.TestCase):
    @patch('download_files_gos_zakupki.is_tender_in_db')
    @patch('download_files_gos_zakupki.process_single_tender_files')
    @patch('download_files_gos_zakupki.get_link_to_file_page')
    @patch('download_files_gos_zakupki.get_all_from_processing_queue')
    def test_download_tenders_files_skips_processed(self, mock_get_all, mock_get_link, mock_process, mock_is_tender_in_db):
        mock_get_all.return_value = [
            {'tender_number': '0311234', 'url': 'http://test', 'law': '44-ФЗ', 'files_downloaded': False}
        ]
        mock_is_tender_in_db.return_value = True

        download_files_gos_zakupki.download_tenders_files()

        mock_get_link.assert_not_called()
        mock_process.assert_not_called()

if __name__ == '__main__':
    unittest.main()
