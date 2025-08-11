# EDINET Downloader

This project downloads filings from the EDINET API and parses the XBRL
files.  `save_xbrl.py` fetches document metadata and body using `type=2`
and then downloads each filing as an XBRL ZIP.
