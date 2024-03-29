"""
This script creates a subset of the raw OIT course-list file, filtering out:
- courses that don't match the specified (via envars) season and year.
- courses that don't match the specified legitimate sections.
- courses that don't have an instructor.

It creates the subset, and, at the end of the logging, a summary of relevant data.
"""

import json, logging, os, pprint, sys

## setup logging ----------------------------------------------------
LOG_PATH: str = os.environ['LGNT__LOG_PATH']
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S' )
log = logging.getLogger(__name__)
log.debug( 'logging ready' )

## update sys.path for project imports  -----------------------------
PROJECT_CODE_DIR = os.environ['LGNT__PROJECT_CODE_DIR']
sys.path.append( PROJECT_CODE_DIR )
from lib.common.validate_files import is_utf8_encoded, is_tab_separated

## grab env vars ----------------------------------------------------
OIT_COURSE_LIST_PATH: str = os.environ['LGNT__COURSES_FILEPATH']
TARGET_SEASON: str = os.environ['LGNT__SEASON']
TARGET_YEAR: str = os.environ['LGNT__YEAR']
LEGIT_SECTIONS: str = json.loads( os.environ['LGNT__LEGIT_SECTIONS_JSON'] )
OIT_SUBSET_01_OUTPUT_PATH: str = '%s/oit_subset_01.tsv' % os.environ['LGNT__CSV_OUTPUT_DIR_PATH']
log.debug( f'OIT_COURSE_LIST_PATH, ``{OIT_COURSE_LIST_PATH}``' )
log.debug( f'TARGET_SEASON, ``{TARGET_SEASON}``' )
log.debug( f'TARGET_YEAR, ``{TARGET_YEAR}``' )
log.debug( f'LEGIT_SECTIONS, ``{LEGIT_SECTIONS}``' )
log.debug( f'OIT_SUBSET_01_OUTPUT_PATH, ``{OIT_SUBSET_01_OUTPUT_PATH}``' )


## controller -------------------------------------------------------

def main():
    """ Controller.
        Called by if __name__ == '__main__' """

    ## validate OIT file --------------------------------------------
    assert is_utf8_encoded(OIT_COURSE_LIST_PATH) == True
    # assert is_tab_separated(OIT_COURSE_LIST_PATH) == True  ## TODO

    ## load OIT file ------------------------------------------------
    lines = []
    with open( OIT_COURSE_LIST_PATH, 'r' ) as f:
        lines = f.readlines()

    ## get heading and data lines -----------------------------------
    heading_line = lines[0]
    parts = heading_line.split( '\t' )
    parts = [ part.strip() for part in parts ]
    log.debug( f'parts, ``{pprint.pformat(parts)}``' )
    data_lines = lines[1:]

    ## make subset --------------------------------------
    skipped_due_to_no_instructor = []
    skipped_sections = []
    subset_lines = []
    for i, data_line in enumerate( data_lines ):
        data_ok = False
        if i < 5:
            log.debug( f'processing data_line, ``{data_line}``' )
        line_dict = parse_line( data_line, heading_line, i )
        course_code_dict = parse_course_code( data_line, i )
        if course_code_dict['course_code_year'] == TARGET_YEAR:
            log.debug( 'passed year check' )
            if course_code_dict['course_code_term'] == TARGET_SEASON:
                log.debug( 'passed season check' )
                if course_code_dict['course_code_section'] in LEGIT_SECTIONS:
                    log.debug( 'passed section check' )
                    data_ok = True
                else:
                    skipped_sections.append( course_code_dict['course_code_section'] )
                if data_ok == True and len( line_dict['ALL_INSTRUCTORS'].strip() ) > 0:
                    log.debug( 'passed instructor check' )
                    subset_lines.append( data_line )
                    log.debug( 'added to subset_lines' )
                else:
                    log.debug( 'skipped due to no instructor' )
                    skipped_due_to_no_instructor.append( data_line )
    # log.debug( f'subset_lines, ``{pprint.pformat(subset_lines)}``' )
    # log.debug( f'len(subset_lines), ``{len(subset_lines)}``' )
    # log.debug( f'skipped_due_to_no_instructor, ``{pprint.pformat(skipped_due_to_no_instructor)}``' )
    # log.debug( f'len(skipped_due_to_no_instructor), ``{len(skipped_due_to_no_instructor)}``' )

    ## populate course-parts buckets --------------------------------
    buckets_dict: dict  = make_buckets()  # returns dict like: ```( course_code_institutions': {'all_values': [], 'unique_values': []}, etc... }```
    for i, summer_line in enumerate( subset_lines ):
        if i < 5:
            log.debug( f'processing summer-line, ``{summer_line}``' )
        course_code_dict = parse_course_code( summer_line, i )
        buckets_dict: dict = populate_buckets( course_code_dict, buckets_dict )
    buckets_dict['skipped_sections_for_target_year_and_season']['all_values'] = skipped_sections
    # log.debug( f'buckets_dict, ``{pprint.pformat(buckets_dict)}``' )

    ## prepare bucket counts ----------------------------------------
    buckets_dict: dict = add_counts( buckets_dict )
    log.debug( f'updated_buckets_dict, ``{pprint.pformat(buckets_dict)}``' )

    ## prep easyview output -----------------------------------------
    # easyview_output = make_easyview_output( buckets_dict )
    easyview_output = make_easyview_output( buckets_dict, skipped_due_to_no_instructor )
    log.debug( f'easyview_output, ``{pprint.pformat(easyview_output)}``' )

    ## write summer-2023 subset to file -----------------------------
    with open( OIT_SUBSET_01_OUTPUT_PATH, 'w' ) as f:
        f.write( heading_line )
        for line in subset_lines:
            f.write( line )
        
    ## end main()


## helper functions -------------------------------------------------

def parse_line( data_line: str, heading_line: str, line_number: int ) -> dict:
    """ Parses data-line.
        Called by main() """
    log.debug( 'starting parse_line()')
    assert type(data_line) == str
    assert type(heading_line) == str
    assert type(line_number) == int
    parts = data_line.split( '\t' )
    parts = [ part.strip() for part in parts ]
    heading_parts = heading_line.split( '\t' )
    heading_parts = [ part.strip() for part in heading_parts ]
    line_dict = {}
    for i, part in enumerate( parts ):
        line_dict[heading_parts[i]] = part
    if line_number < 5:
        log.debug( f'line_dict, ``{pprint.pformat(line_dict)}``' )
    return line_dict


def make_easyview_output( buckets_dict: dict, skipped_due_to_no_instructor: list ) -> dict:
    """ Prepares easyview output.
        Called by main() """
    assert type(buckets_dict) == dict
    output_dict = {}
    for key in buckets_dict.keys():
        unsorted_unique_values = buckets_dict[key]['unique_values']
        # sorted_unique_values = sorted( unsorted_unique_values, key=lambda x: x[1], reverse=True )
        ## sort by count and then by string
        # sorted_unique_values = sorted( unsorted_unique_values, key=lambda x: (x[1], x[0]), reverse=True )
        ## sort by count-descending, and then by string-ascending
        sorted_unique_values = sorted( unsorted_unique_values, key=lambda x: (-x[1], x[0]) )        
        output_dict[key] = sorted_unique_values
    output_dict['skipped_instructor_count_for_target_year_and_season_and_section'] = len( skipped_due_to_no_instructor )
    # jsn = json.dumps( output_dict, indent=2 )
    # with open( './output.json', 'w' ) as f:
    #     f.write( jsn )
    return output_dict


def add_counts( buckets_dict: dict ) -> dict:
    """ Updates 'unique_set': {'count': 0, 'unique_values': []} """
    assert type(buckets_dict) == dict
    for key in buckets_dict.keys():
        log.debug( f'key, ``{key}``' ) 
        unique_values_from_set = list( set( buckets_dict[key]['all_values'] ) )
        unique_tuple_list = [ (value, buckets_dict[key]['all_values'].count(value)) for value in unique_values_from_set ]
        log.debug( f'unique_tuple_list, ``{unique_tuple_list}``' )
        buckets_dict[key]['unique_values'] = unique_tuple_list
    # log.debug( f'buckets_dict, ``{pprint.pformat(buckets_dict)}``' )
    return buckets_dict


def populate_buckets( course_code_dict: dict, buckets_dict: dict ) -> dict:
    """ Populates buckets. """
    assert type(course_code_dict) == dict
    assert type(buckets_dict) == dict
    for key in course_code_dict.keys():
        if key == 'course_code_institution':
            buckets_dict['subset_institutions']['all_values'].append( course_code_dict[key] )
        elif key == 'course_code_department':
            buckets_dict['subset_departments']['all_values'].append( course_code_dict[key] )
        elif key == 'course_code_year':
            buckets_dict['subset_years']['all_values'].append( course_code_dict[key] )
        elif key == 'course_code_term':
            buckets_dict['subset_terms']['all_values'].append( course_code_dict[key] )
        elif key == 'course_code_section':
            buckets_dict['subset_sections']['all_values'].append( course_code_dict[key] )
    return buckets_dict


def make_buckets() -> dict:
    """ Returns dict of buckets. """
    buckets_dict = {
        'subset_institutions': { 
            'all_values': [], 
            'unique_values': [] },
        'subset_departments': { 
            'all_values': [], 
            'unique_values': [] },
        'subset_years': { 
            'all_values': [], 
            'unique_values': [] },
        'subset_terms': { 
            'all_values': [], 
            'unique_values': [] },
        'subset_sections': { 
            'all_values': [], 
            'unique_values': [] },
        'skipped_sections_for_target_year_and_season': { 
            'all_values': [], 
            'unique_values': [] },
        }
    log.debug( f'initialized buckets_dict, ``{pprint.pformat(buckets_dict)}``' )
    return buckets_dict


def parse_course_code( data_line, i ):
    """ Parses course-code into dict. """
    assert type(data_line) == str
    assert type(i) == int
    parts = data_line.split( '\t' )
    parts = [ part.strip() for part in parts ]
    ## parse course code --------------------------------------------
    course_code_parts: list = parts[0].split( '.' )
    if i < 5:
        log.debug( f'processing course_code_parts, ``{course_code_parts}``' )
    course_code_dict = {
        'course_code_institution': course_code_parts[0],
        'course_code_department': course_code_parts[1],
        'course_code_number': course_code_parts[2],
        'course_code_year_and_term': course_code_parts[3],
        # 'course_code_section': course_code_parts[4] 
        }
    ## handle missing section
    if len(course_code_parts) == 5:
        course_code_dict['course_code_section'] = course_code_parts[4]
    else:
        log.debug( 'adding EMPTY section' )
        course_code_dict['course_code_section'] = 'EMPTY'
        # course_code_section_missing_count += 1
    ## handle year and term
    course_code_year = course_code_parts[3].split('-')[0]
    course_code_term = course_code_parts[3].split('-')[1]
    course_code_dict['course_code_year'] = course_code_year
    course_code_dict['course_code_term'] = course_code_term
    if i < 5:
        log.debug( f'course_code_dict, ``{pprint.pformat(course_code_dict)}``' )
    return course_code_dict


## add if name == main...
if __name__ == '__main__':
    main()
    sys.exit(0)


   ## set up buckets
    # missing_institutions = []
    # missing_departments = []
    # missing_numbers = []
    # missing_years = []
    # missing_terms = []
    # missing_sections = []
    # course_code_institutions = []
    # course_code_departments = []
    # # course_code_numbers = []  ## don't need to populate this
    # course_code_years = []
    # course_code_terms = []
    # course_code_sections = []
    # course_code_section_missing_count = 0
    # summer_2023_lines = []

    ## make summer-2023 subset -
    # for i, data_line in enumerate( data_lines ):
    #     log.debug( f'processing data_line, ``{data_line}``' )
    #     parts = data_line.split( '\t' )
    #     parts = [ part.strip() for part in parts ]
    #     ## parse course code --------------------------------------------
    #     course_code_parts: list = parts[0].split( '.' )
    #     log.debug( f'processing course_code_parts, ``{course_code_parts}``' )
    #     course_code_dict = {
    #         'course_code_institution': course_code_parts[0],
    #         'course_code_department': course_code_parts[1],
    #         'course_code_number': course_code_parts[2],
    #         'course_code_year_and_term': course_code_parts[3],
    #         # 'course_code_section': course_code_parts[4] 
    #         }
    #     ## handle missing section
    #     if len(course_code_parts) == 5:
    #         course_code_dict['course_code_section'] = course_code_parts[4]
    #     else:
    #         log.debug( 'adding EMPTY section' )
    #         course_code_dict['course_code_section'] = 'EMPTY'
    #         course_code_section_missing_count += 1
    #     ## handle year and term
    #     course_code_year = course_code_parts[3].split('-')[0]
    #     course_code_term = course_code_parts[3].split('-')[1]
    #     course_code_dict['course_code_year'] = course_code_year
    #     course_code_dict['course_code_term'] = course_code_term
    #     if i < 5:
    #         log.debug( f'course_code_dict, ``{pprint.pformat(course_code_dict)}``' )
    #     # if i > 6:
    #     #     break
    #     ## evaluate for summer-2023 --------------------------------------

#     ## checks...
#     if course_code_dict['course_code_institution'].strip() == '':
#         missing_institutions.append( course_code_dict )
#     if course_code_dict['course_code_department'].strip() == '':
#         missing_departments.append( course_code_dict )
#     if course_code_dict['course_code_number'].strip() == '':
#         missing_numbers.append( course_code_dict )
#     if course_code_dict['course_code_year'].strip() == '':
#         missing_years.append( course_code_dict )
#     if course_code_dict['course_code_term'].strip() == '':
#         missing_terms.append( course_code_dict )
#     if course_code_dict['course_code_section'].strip() == '':
#         missing_sections.append( course_code_dict )
#     ## collect...
#     if course_code_dict['course_code_institution'] not in course_code_institutions:
#         course_code_institutions.append( course_code_dict['course_code_institution'] )
#     if course_code_dict['course_code_department'] not in course_code_departments:       
#         course_code_departments.append( course_code_dict['course_code_department'] )
#     if course_code_dict['course_code_year'] not in course_code_years:
#         course_code_years.append( course_code_dict['course_code_year'] )
#     if course_code_dict['course_code_term'] not in course_code_terms:
#         course_code_terms.append( course_code_dict['course_code_term'] )
#     if course_code_dict['course_code_section'] not in course_code_sections:
#         course_code_sections.append( course_code_dict['course_code_section'] )

# ## log results ------------------------------------------------------
# log.debug( f'OIT course entries count, ``{len(data_lines)}``' )
# log.debug( f'missing_departments, ``{pprint.pformat(sorted(missing_departments))}``' )
# log.debug( f'missing_numbers, ``{pprint.pformat(sorted(missing_numbers))}``' )
# log.debug( f'missing_years, ``{pprint.pformat(sorted(missing_years))}``' )
# log.debug( f'missing_terms, ``{pprint.pformat(sorted(missing_terms))}``' )
# log.debug( f'missing_sections, ``{pprint.pformat(sorted(missing_sections))}``' )
# log.debug( f'course_code_institutions, ``{pprint.pformat(sorted(course_code_institutions))}``' )
# log.debug( f'course_code_departments, ``{pprint.pformat(sorted(course_code_departments))}``' )
# # log.debug( f'course_code_numbers, ``{pprint.pformat(course_code_numbers)}``' )
# log.debug( f'course_code_years, ``{pprint.pformat(sorted(course_code_years))}``' )
# log.debug( f'course_code_terms, ``{pprint.pformat(sorted(course_code_terms))}``' )
# log.debug( f'course_code_sections, ``{pprint.pformat(sorted(course_code_sections))}``' )
# log.debug( f'course_code_section_missing_count, ``{course_code_section_missing_count}``' )


# def make_easyview_output( buckets_dict: dict ) -> str:
#     """ Prepares easyview output.
#         Called by main() """
#     assert type(buckets_dict) == dict
#     output = ''
#     for key in buckets_dict.keys():
#         # output += f'{key}:\n'
#         header = f'{key}:'
#         data = ''
#         for item in buckets_dict[key]['unique_values']:
#             data += f'  {item[0]} ({item[1]})\n'
#         ## sort by count
#         data = ''.join( sorted( data.split('\n') ) )
#         output += f'{header}\n{data}'

#             # output += f'  {item[0]} ({item[1]})\n'
#     return output


# def make_easyview_output( buckets_dict: dict ) -> str:
#     """ Prepares easyview output.
#         Called by main() """
#     assert type(buckets_dict) == dict
#     output = ''
#     for key in buckets_dict.keys():
#         output += f'{key}:\n'
#         for item in buckets_dict[key]['unique_values']:
#             output += f'  {item[0]} ({item[1]})\n'
#     return output


## example course code
# brown.afri.0090.2023-fall.s01

