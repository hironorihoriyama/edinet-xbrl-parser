# EDINET Downloader

This project downloads filings from the EDINET API and parses the XBRL
files.  `save_xbrl.py` fetches document metadata using `type=1` (metadata only)
for faster retrieval and then downloads each filing as an XBRL ZIP.
