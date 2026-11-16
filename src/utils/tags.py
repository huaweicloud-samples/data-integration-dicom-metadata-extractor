# DICOM Value Representation (VR) tag processing
# http://dicom.nema.org/dicom/2013/output/chtml/part05/sect_6.2.html
# This module relies only on pydicom for DICOM tag extraction.

import datetime
import base64
import math
import os
from logger import get_logger
import pydicom

IGNORE_OB = os.getenv('IGNORE_OB', True)

log = get_logger(__name__)


def rep_string(elem):
    return serialize_sets(elem)


def convert_DA(elem):
    """Convert DICOM DA (Date) to ISO format for DATE type compatibility."""
    try:
        if not elem.is_empty:
            date = rep_string(elem)
            if isinstance(date, list):
                date_list = []
                for item in date:
                    date_list.append(
                        datetime.datetime.strptime(item, '%Y%m%d').date())
                return date_list
            return datetime.datetime.strptime(date, '%Y%m%d').date()
        return datetime.datetime.fromisoformat('1900-01-01').date()
    except Exception as e:
        log.error(e)
        raise


def convert_OB(elem):
    try:
        if elem.is_empty:
            return elem.value
        if IGNORE_OB:
            return 'IGNORED'
        else:
            return base64.standard_b64encode(elem.value)
    except Exception as e:
        log.error(e)
        raise


def convert_TM(elem):
    # Return string; DLI does not support TIME data type (HHMMSS.FFFFFF)
    return rep_string(elem)


def generate_PN(elem):
    return {
        'FamilyName': elem.family_name,
        'GivenName': elem.given_name,
        'Ideographic': elem.ideographic,
        'MiddleName': elem.middle_name,
        'NamePrefix': elem.name_prefix,
        'NameSuffix': elem.name_suffix,
        'Phonetic': elem.phonetic,
    }


def convert_PN(elem):
    try:
        if elem.is_empty:
            return {
                'FamilyName': '',
                'GivenName': '',
                'Ideographic': '',
                'MiddleName': '',
                'NamePrefix': '',
                'NameSuffix': '',
                'Phonetic': '',
            }
        data = rep_string(elem)
        if isinstance(data, list):
            pn_list = []
            for item in data:
                pn_list.append(generate_PN(item))
            return pn_list
        else:
            return generate_PN(elem.value)
    except Exception as e:
        log.error(e)
        raise


def serialize_sets(obj):
    try:
        return validate_vm(obj)
    except Exception as e:
        log.error(e)
        raise


def validate_vm(obj):
    """Validate Value Multiplicity and return appropriate Python type."""
    try:
        log.debug(f'Validating Tag {obj.keyword} VM: {obj.VM} VR: {obj.VR}')
        max_vm = pydicom._dicom_dict.DicomDictionary[obj.tag][1]
        split = max_vm.split('-')
        if len(split) > 1:
            min_val = split[0]
            max_val = split[1]
            if 'n' in max_val:
                max_val = math.inf
            else:
                max_val = int(max_val)
        else:
            min_val = int(split[0])
            max_val = min_val
        if max_val > 1:
            if isinstance(obj.value, pydicom.multival.MultiValue):
                return obj.value._list
            elif isinstance(obj.value, list):
                return obj.value
            else:
                return [obj.value]
        else:
            return str(obj.value)
    except Exception as e:
        log.error(e)
        raise


def convert_SQ(elem):
    """Convert DICOM SQ (Sequence) to nested dictionary."""
    try:
        sq = {}
        if not elem.is_empty:
            for item in elem.value._list:
                if item == pydicom.Dataset():
                    return None
                for i in item:
                    sq[i.keyword] = vr_select(i)(i)
            return sq
        return rep_string(elem)
    except Exception as e:
        log.error(e)
        raise


def return_integer(elem):
    try:
        if not elem.is_empty:
            return rep_string(elem)
        return int(0)
    except Exception as e:
        log.error(e)
        raise


def return_float(elem):
    try:
        if not elem.is_empty:
            return rep_string(elem)
        return float(0)
    except Exception as e:
        log.error(e)
        raise


def convert_DT(elem):
    """Convert DICOM DT (DateTime) - returns raw value as string."""
    try:
        if not elem.is_empty:
            date = rep_string(elem)
            if isinstance(date, list):
                return elem.value
            return elem.value
        return elem.value
    except Exception as e:
        log.error(e)
        raise


def vr_select(elem):
    """Select the appropriate conversion function based on the VR type."""
    return {
        'AE': rep_string,
        'AS': rep_string,
        'AT': return_integer,
        'CS': rep_string,
        'DA': convert_DA,
        'DS': rep_string,
        'DT': convert_DT,
        'FD': rep_string,
        'FL': return_float,
        'IS': rep_string,
        'LO': rep_string,
        'LT': rep_string,
        'OB': rep_string,
        'OD': rep_string,
        'OF': rep_string,
        'OL': rep_string,
        'OW': rep_string,
        'OV': rep_string,
        'PN': convert_PN,
        'SH': rep_string,
        'SL': return_integer,
        'SQ': convert_SQ,
        'SS': return_integer,
        'ST': rep_string,
        'SV': rep_string,
        'TM': convert_TM,
        'UC': rep_string,
        'UI': rep_string,
        'UL': return_integer,
        'UN': rep_string,
        'UR': rep_string,
        'US': return_integer,
        'UT': rep_string,
        'UV': rep_string,
    }.get(elem.VR, f'Invalid VR {elem.VR} tag')
