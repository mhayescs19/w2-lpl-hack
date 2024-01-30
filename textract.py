import boto3
import sys
import re
import json
from collections import defaultdict

import io
import os

from pdf2image import convert_from_path
import boto3
from io import BytesIO

session = boto3.Session(region_name="us-east-1")
client = session.client("textract")

whitelist_fields = [
    '9',
    'Third-party sick pay',
    "c Employer's name, address, and ZIP code",
    'Retirement plan',
    '16 State wages, tips, etc.',
    'State',
    '12a',
    '12b',
    '3 Social security wages',
    '17 State income tax',
    'd Control number',
    '7 Social security tips',
    '8 Allocated tips',
    '1 Wages, tips, other compensation',
    'OMB No.',
    "e Employee's first name and initial Last name Suff.",
    'b Employer identification number (EIN)',
    '2 Federal income tax withheld',
    '20 Locality name',
    '12c',
    "a Employee's social security number",
    '11 Nonqualified plans',
    '4 Social security tax withheld',
    '19 Local income tax',
    '18 Local wages, tips, etc.',
    '10 Dependent care benefits',
    '14 Other',
    '6 Medicare tax withheld',
    '12d',
    '5 Medicare wages and tips',
    "Employer's state ID number",
    'Statutory employee',
    "f Employee's address and ZIP code",
]


def pdf_to_image(image="static/fw2.pdf"):
    return convert_from_path(image)[0]  # list of pages, not single page


def convert_image_tob64(img):
    buffer = io.BytesIO()
    pdf_to_image(img).save(buffer, format="JPEG")
    # img_str_64 = base64.b64encode(buffer.getvalue())
    return buffer.getvalue()


def get_kv_map(file_location):
    bytes = None
    if file_location.endswith(".pdf"):
        bytes = convert_image_tob64(file_location)
    else:
        bytes = open(file_location, "rb").read()
    response = client.analyze_document(Document={'Bytes': bytes}, FeatureTypes=['FORMS'])

    # Get the text blocks
    blocks = response['Blocks']

    # get key and value maps
    key_map = {}
    value_map = {}
    block_map = {}
    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            if 'KEY' in block['EntityTypes']:
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    return key_map, value_map, block_map


def get_kv_relationship(key_map, value_map, block_map):
    kvs = defaultdict(list)
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key = get_text(key_block, block_map)
        val = get_text(value_block, block_map)
        kvs[key].append(val)
    return kvs


def find_value_block(key_block, value_map):
    for relationship in key_block['Relationships']:
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = value_map[value_id]
    return value_block


def get_text(result, blocks_map):
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + ' '
                    if word['BlockType'] == 'SELECTION_ELEMENT':
                        if word['SelectionStatus'] == 'SELECTED':
                            text += 'X '

    return text


def print_kvs(kvs):
    for key, value in kvs.items():
        print(key, ":", value)


def post_proces_text(kvs: dict):
    clean_map = {}
    for k, v in kvs.items():
        k = k.strip()
        for idx, item in enumerate(v):
            v[idx] = item.strip()
        clean_map[k] = v
    return dict((k, v) for k, v in clean_map.items() if k in whitelist_fields)  # filter out keys that are irregular


def search_value(kvs, search_key):
    for key, value in kvs.items():
        if re.search(search_key, key, re.IGNORECASE):
            return value


def init_text_search(filename):
    key_map, value_map, block_map = get_kv_map(filename)
    return post_proces_text(get_kv_relationship(key_map, value_map, block_map))


def main():
    key_map, value_map, block_map = get_kv_map()

    # Get Key Value relationship
    kvs = get_kv_relationship(key_map, value_map, block_map)
    print("\n\n== FOUND KEY : VALUE pairs ===\n")
    print_kvs(kvs)

    # Start searching a key value
    while input('\n Do you want to search a value for a key? (enter "n" for exit) ') != 'n':
        search_key = input('\n Enter a search key:')
        print('The value is:', search_value(kvs, search_key))


if __name__ == "__main__":
    main()
