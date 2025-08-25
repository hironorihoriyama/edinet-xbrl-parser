# tests/test_edinet_tools.py

import os
import sys
import pytest

# Ensure src directory is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from edinet_tools import filter_by_codes

sample_docs = [
    {"edinetCode": "E00001", "docTypeCode": "120", "name": "doc1"},
    {"edinetCode": "E00002", "docTypeCode": "130", "name": "doc2"},
    {"edinetCode": "E00001", "docTypeCode": "130", "name": "doc3"},
]


def test_filter_by_list_codes():
    result = filter_by_codes(sample_docs, edinet_codes=["E00001"], doc_type_codes=["120"])
    assert result == [sample_docs[0]]


def test_filter_by_string_codes():
    result = filter_by_codes(sample_docs, edinet_codes="E00001", doc_type_codes="130")
    assert result == [sample_docs[2]]
