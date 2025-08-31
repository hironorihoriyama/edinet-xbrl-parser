"""Helpers for interacting with the EDINET API."""

import datetime
import json
import os  # For os.path.join and similar utilities.
import urllib.parse
import urllib.request
from typing import List, Dict, Union

# API keys (e.g., via load_dotenv) are expected to be loaded by the caller.


def filter_by_codes(
    docs: List[Dict],
    edinet_codes: Union[List[str], str] = [],
    doc_type_codes: Union[List[str], str] = [],
) -> List[Dict]:
    """Filter disclosure document metadata by EDINET and document type codes.

    Args:
        docs (List[Dict]): List of document metadata dictionaries.
        edinet_codes (Union[List[str], str], optional): EDINET codes to keep.
        doc_type_codes (Union[List[str], str], optional): Document type codes to
            keep.

    Returns:
        List[Dict]: Filtered list of documents.
    """
    if len(edinet_codes) == 0:
        # If edinet_codes is empty, target all edinetCode values.
        edinet_codes = [
            doc["edinetCode"]
            for doc in docs
            if "edinetCode" in doc and doc["edinetCode"] is not None
        ]
    elif isinstance(edinet_codes, str):
        edinet_codes = [edinet_codes]

    if len(doc_type_codes) == 0:
        # If doc_type_codes is empty, target all docTypeCode values.
        doc_type_codes = [
            doc["docTypeCode"]
            for doc in docs
            if "docTypeCode" in doc and doc["docTypeCode"] is not None
        ]
    elif isinstance(doc_type_codes, str):
        doc_type_codes = [doc_type_codes]

    return [
        doc
        for doc in docs
        if doc.get("edinetCode") in edinet_codes
        and doc.get("docTypeCode") in doc_type_codes
    ]


def disclosure_documents(
    date: Union[str, datetime.date], api_key: str, type: int = 2
) -> Dict:
    """Retrieve disclosure document metadata for a given date.

    Args:
        date (Union[str, datetime.date]): Target date.
        api_key (str): EDINET API key.
        type (int, optional): API type parameter; ``2`` retrieves metadata and
            body. Defaults to ``2``.

    Returns:
        Dict: JSON response from the EDINET API.
    """
    if isinstance(date, str):
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date string. Use format 'YYYY-MM-DD'")
        date_str = date
    elif isinstance(date, datetime.date):
        date_str = date.strftime("%Y-%m-%d")
    else:
        raise TypeError("Date must be a string ('YYYY-MM-DD') or datetime.date")

    # Endpoint for EDINET document list API [3].
    url = "https://disclosure.edinet-fsa.go.jp/api/v2/documents.json"
    params = {
        "date": date_str,
        "type": type,  # "2" retrieves metadata and body [3].
        "Subscription-Key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    with urllib.request.urlopen(full_url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_document(doc_id: str, api_key: str) -> urllib.request.urlopen:
    """Download the body of a document by its ID.

    Args:
        doc_id (str): Document ID.
        api_key (str): EDINET API key.

    Returns:
        urllib.request.urlopen: Response object for the download.
    """
    # Endpoint for EDINET document retrieval API [4].
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}"
    params = {
        "type": 1,  # "1": XBRL format, "5": CSV format.
        "Subscription-Key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"

    return urllib.request.urlopen(full_url)


def save_document(doc_res: urllib.request.urlopen, output_path: str) -> None:
    """Save the downloaded content to a file.

    Args:
        doc_res (urllib.request.urlopen): Response object containing data.
        output_path (str): Destination file path.
    """
    with open(output_path, "wb") as file_out:
        file_out.write(doc_res.read())
    print(f"Saved: {output_path}")


def get_documents_for_date_range(
    start_date: datetime.date,
    end_date: datetime.date,
    api_key: str,
    edinet_codes: List[str] = [],
    doc_type_codes: List[str] = [],
) -> List[Dict]:
    """Collect documents for a range of dates and filter by codes.

    Args:
        start_date (datetime.date): Start date.
        end_date (datetime.date): End date.
        api_key (str): EDINET API key.
        edinet_codes (List[str], optional): EDINET codes to keep.
        doc_type_codes (List[str], optional): Document type codes to keep.

    Returns:
        List[Dict]: Filtered list of document metadata.
    """
    matching_docs: List[Dict] = []
    current_date = start_date

    while current_date <= end_date:
        # Pass the API key to disclosure_documents.
        docs_res = disclosure_documents(date=current_date, api_key=api_key)
        if docs_res.get("results"):
            # filter_by_codes does not require the API key.
            filtered_docs = filter_by_codes(
                docs_res["results"], edinet_codes, doc_type_codes
            )
            matching_docs.extend(filtered_docs)
        current_date += datetime.timedelta(days=1)

    return matching_docs

