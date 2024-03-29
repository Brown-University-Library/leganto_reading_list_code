"""
Main manager file to produce reading lists.
"""

import argparse, datetime, json, logging, os, pprint, sys

import gspread, pymysql
from lib import csv_maker
from lib import db_stuff
from lib import gsheet_prepper
from lib import leganto_final_processor
from lib import loaders
from lib import readings_extractor
from lib import readings_processor
from lib.cdl import CDL_Checker
from lib.loaders import OIT_Course_Loader


LOG_PATH: str = os.environ['LGNT__LOG_PATH']
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S' )
log = logging.getLogger(__name__)
log.debug( 'logging ready' )


def manage_build_reading_list( course_id_input: str, update_ss: bool, force: bool, range_arg: dict ):
    """ Manages db-querying, assembling, and posting to gsheet. 
        Called by if...main: """
    log.debug( f'raw course_id, ``{course_id_input}``; update_ss, ``{update_ss}``; force, ``{force}``; range_arg, ``{range_arg}``')
    assert type(course_id_input) == str, type(course_id_input)
    assert type(update_ss) == bool, type(update_ss)
    assert type(force) == bool, type(force)
    assert type(range_arg) == dict, type(range_arg)
    ## settings -----------------------------------------------------
    settings: dict = load_initial_settings()
    ## load/prep necessary data -------------------------------------
    err: dict = loaders.rebuild_pdf_data_if_necessary( {'days': settings["PDF_OLDER_THAN_DAYS"]} )
    if err:
        raise Exception( f'problem rebuilding pdf-json, error-logged, ``{err["err"]}``' )  
    oit_course_loader = OIT_Course_Loader( settings['COURSES_FILEPATH'] )  # instantiation loads data from file into list of dicts
    ## prep course_id_list ------------------------------------------
    course_id_list: list = prep_course_id_list( course_id_input, settings, oit_course_loader, range_arg )
    ## prep class-info-dicts ----------------------------------------
    classes_info: list = prep_classes_info( course_id_list, oit_course_loader )
    ## prep basic data ----------------------------------------------
    basic_data: list = prep_basic_data( classes_info, settings, oit_course_loader )
    ## prep leganto data --------------------------------------------
    leganto_data: list = prep_leganto_data( basic_data, settings )
    ## update tracker if necessary ----------------------------------
    if course_id_input == 'oit_file':
        oit_course_loader.update_tracker( leganto_data, settings )
    ## update spreadsheet if necessary ------------------------------
    if update_ss:
        log.info( f'update_ss is ``{update_ss}``; will update gsheet' )
        # gsheet_prepper.update_gsheet( leganto_data, settings['CREDENTIALS'], settings['SPREADSHEET_NAME'] )
        gsheet_prepper.update_gsheet( basic_data, leganto_data, settings['CREDENTIALS'], settings['SPREADSHEET_NAME'] )
    else:
        log.info( f'update_ss is ``{update_ss}``; not updating gsheet' )
    ## create .csv file ---------------------------------------------
    csv_maker.create_csv( leganto_data, leganto_final_processor.get_headers() )
    log.info( 'csv produced' )

    ## end def manage_build_reading_list()


def load_initial_settings() -> dict:
    """ Loads envar settings.
        Called by manage_build_reading_list() """
    settings = {
        'COURSES_FILEPATH': os.environ['LGNT__COURSES_FILEPATH'],                   # path to OIT course-data
        'PDF_OLDER_THAN_DAYS': 30,                                                  # to ascertain whether to requery OCRA for pdf-data
        'CREDENTIALS': json.loads( os.environ['LGNT__SHEET_CREDENTIALS_JSON'] ),    # gspread setting
        'SPREADSHEET_NAME': os.environ['LGNT__SHEET_NAME'],                         # gspread setting
        'LAST_CHECKED_PATH': os.environ['LGNT__LAST_CHECKED_JSON_PATH'],            # contains last-run spreadsheet course-IDs
        'PDF_JSON_PATH': os.environ['LGNT__PDF_JSON_PATH'],                         # pre-extracted pdf data
        'FILES_URL_PATTERN': os.environ['LGNT__FILES_URL_PATTERN'],                 # pdf-url
        'TRACKER_JSON_FILEPATH': os.environ['LGNT__TRACKER_JSON_FILEPATH'],         # json-tracker filepath
    }
    PDF_DATA = {}
    with open( settings['PDF_JSON_PATH'], encoding='utf-8' ) as f_reader:
        jsn: str = f_reader.read()
        PDF_DATA = json.loads( jsn )
    log.debug( f'PDF_DATA (partial), ``{pprint.pformat(PDF_DATA)[0:1000]}``' )
    settings['PDF_DATA'] = PDF_DATA
    log.debug( f'settings-keys, ``{pprint.pformat( sorted(list(settings.keys())) )}``' )
    return settings


def prep_course_id_list( course_id_input: str, settings: dict, oit_course_loader: OIT_Course_Loader, range_arg: dict ) -> list:
    """ Prepares list of oit-coursecodes from course_id_input.
        Simplistic coursecodes come from command-line specification, i.e. HIST1234, or from spreadsheet.
        OIT coursecodes come from the course_id_input == 'oit_file' case.
        Called by manage_build_reading_list() """
    log.debug( f'course_id_input, ``{course_id_input}``' )
    oit_coursecode_list = []
    simplistic_coursecode_list = []
    if course_id_input == 'SPREADSHEET':
        simplistic_coursecode_list: list = get_list_from_spreadsheet( settings )
        if force:
            log.info( 'skipping recent-updates check' )
        else:
            ## check for recent updates -----------------------------
            recent_updates: bool = check_for_updates( simplistic_coursecode_list, settings )
            if recent_updates == False:
                log.info( 'no recent updates' )
                simplistic_coursecode_list = []
            else:
                log.info( 'recent updates found' )
    elif course_id_input == 'oit_file':
        oit_coursecode_list: list = oit_course_loader.grab_course_list( range_arg )
        oit_coursecode_list = oit_course_loader.remove_already_processed_courses( oit_coursecode_list, settings )
        oit_course_loader.populate_tracker( oit_coursecode_list )
    else:
        simplistic_coursecode_list: list = course_id_input.split( ',' )
    log.debug( f'simplistic_coursecode_list, ``{pprint.pformat(simplistic_coursecode_list)}``' )
    log.debug( f'oit_coursecode_list, ``{pprint.pformat(oit_coursecode_list)}``' )
    all_coursecodes: list = simplistic_coursecode_list + oit_coursecode_list
    log.debug( f'all_coursecodes, ``{pprint.pformat(all_coursecodes)}``' )
    return all_coursecodes


def get_list_from_spreadsheet( settings: dict ) -> list:
    """ Builds course-id-list from spreadsheet.
        Called by prep_course_id_list() """
    credentialed_connection = gspread.service_account_from_dict( settings['CREDENTIALS'] )
    sheet = credentialed_connection.open( settings['SPREADSHEET_NAME'] )
    wrksheet = sheet.worksheet( 'course_ids_to_check' )
    list_of_dicts: list = wrksheet.get_all_records()
    log.debug( f'list_of_dicts, ``{pprint.pformat(list_of_dicts)}``' )
    course_id_list: list = []
    for dct in list_of_dicts:
        # course_id: str = dct['course_id']
        course_id: str = str( dct.get('course_id', '') )
        course_id_list.append( course_id )
    course_id_list.sort()
    log.debug( f'course_id_list from spreadsheet, ``{pprint.pformat(course_id_list)}``' )
    return course_id_list


def check_for_updates( course_id_list: list, settings: dict ) -> bool:
    """ Checks if there have been new updates.
        Can't calculate this by checking `sheet.lastUpdateTime`, because any run _will_ create a recent spreadsheet update.
        So, plan is to look at the root-page columns and compare it agains a saved json file.
        Called by prep_course_id_list() """
    log.debug( f'course_id_list, ``{pprint.pformat(course_id_list)}``' )
    last_saved_list = []
    new_updates_exist = False
    ## load last-saved file -----------------------------------------
    last_saved_list = []
    with open( settings['LAST_CHECKED_PATH'], 'r' ) as f_reader:
        jsn_list = f_reader.read()
        last_saved_list: list = json.loads( jsn_list )
        log.debug( f'last_saved_list, ``{last_saved_list}``' )
        last_saved_list: list = sorted( json.loads(jsn_list) )
        log.debug( f'sorted-last_saved_list, ``{last_saved_list}``' )
        # log.debug( f'last_saved_list from disk, ``{pprint.pformat( sorted(last_saved_list) )}``' )
    if last_saved_list == course_id_list:
        log.debug( f'was _not_ recently updated')
    else:
        new_updates_exist = True
        jsn = json.dumps( course_id_list, indent=2 )
        with open( settings['LAST_CHECKED_PATH'], 'w' ) as f_writer:
            f_writer.write( jsn )
        log.debug( 'new updates found and saved' )
    log.debug( f'new_updates_exist, ``{new_updates_exist}``' )
    return new_updates_exist


def prep_classes_info( course_id_list: list, oit_course_loader: OIT_Course_Loader ) -> list:
    """ Takes list of course_ids -- whether simplistic-coursecodes or oit-coursecodes -- and adds required minimal info using OIT data.
        Called by manage_build_reading_list() """
    log.debug( f'(temp) course_id_list, ``{pprint.pformat( course_id_list )}``' )
    classes_info = []
    for entry in course_id_list:  # with the oit-coursecode, get necessary OIT data
        course_id_entry: str = entry
        log.debug( f'course_id_entry, ``{course_id_entry}``' )
        oit_course_data: list = oit_course_loader.grab_oit_course_data( course_id_entry )
        log.debug( f'oit_course_data, ``{oit_course_data}``' )
        for entry in oit_course_data:
            oit_course_data_entry: dict = entry
            log.debug( f'oit_course_data_entry, ``{oit_course_data_entry}``' )
            leganto_course_id: str = oit_course_data_entry['COURSE_CODE'] if oit_course_data_entry else f'oit_course_code_not_found_for__{course_id_entry}'
            leganto_course_title: str = oit_course_data_entry['COURSE_TITLE'] if oit_course_data_entry else ''
            leganto_section_code: str = oit_course_data_entry['SECTION_ID'] if oit_course_data else ''
            simplistic_courseid = oit_course_loader.convert_oit_course_code_to_plain_course_code( leganto_course_id )
            class_id_entries: list = get_class_id_entries( simplistic_courseid )  # gets class-id used for db lookups
            for class_id_entry in class_id_entries:
                class_info_dict: dict = { 
                    'course_id': course_id_entry, 
                    'class_id': class_id_entry, 
                    'leganto_course_id': leganto_course_id,
                    'leganto_course_title': leganto_course_title,
                    'leganto_section_code': leganto_section_code }
                classes_info.append( class_info_dict )
    log.debug( f'classes_info, ``{pprint.pformat(classes_info)}``' )
    return classes_info


def get_class_id_entries( course_id: str ) -> list:
    """ Finds one or more class_id entries from given course_id.
        Called by manage_build_reading_list() -> prep_classes_info() """
    class_id_list = []
    ## split the id -------------------------------------------------
    db_connection: pymysql.connections.Connection = db_stuff.get_db_connection()  # connection configured to return rows in dictionary format
    split_position: int = 0
    for ( i, character ) in enumerate( course_id ): 
        if character.isalpha():
            pass
        else:
            split_position = i
            break
    ( subject_code, course_code ) = ( course_id[0:split_position], course_id[split_position:] ) 
    log.debug( f'subject_code, ``{subject_code}``; course_code, ``{course_code}``' )
    ## run query to get class_id entries ----------------------------
    sql = f"SELECT * FROM `banner_courses` WHERE `subject` LIKE '{subject_code}' AND `course` LIKE '{course_code}' ORDER BY `banner_courses`.`term` DESC"
    log.debug( f'sql, ``{sql}``' )
    result_set: list = []
    with db_connection:
        with db_connection.cursor() as db_cursor:
            db_cursor.execute( sql )
            result_set = list( db_cursor.fetchall() )  # list() only needed for pylance type-checking
            assert type(result_set) == list
    log.debug( f'result_set, ``{result_set}``' )
    if result_set:
        for entry in result_set:
            class_id = entry.get( 'classid', None )
            if class_id:
                class_id_str = str( class_id )
                class_id_list.append( class_id_str )
        if len( result_set ) > 1:
            log.debug( f'more than one class-id found for course_id, ``{course_id}``' )
    log.debug( f'class_id_list, ``{class_id_list}``' )
    return class_id_list

    ## end def get_class_id_entries()


def prep_basic_data( classes_info: list, settings: dict, oit_course_loader ) -> list:
    """ Queries OCRA and builds initial data.
        Called by manage_build_reading_list() """
    all_results: list = []
    cdl_checker = CDL_Checker()
    for class_info_entry in classes_info:
        assert type(class_info_entry) == dict
        log.debug( f'class_info_entry, ``{class_info_entry}``' )
        class_id: str = class_info_entry['class_id']
        course_id: str = class_info_entry['course_id']
        leganto_course_id: str = class_info_entry['leganto_course_id']
        leganto_section_id: str = class_info_entry['leganto_section_code']
        leganto_course_title: str = class_info_entry['leganto_course_title']
        if class_id:
            ## ------------------------------------------------------
            ## GET OCRA DATA ----------------------------------------
            ## ------------------------------------------------------
            ## ocra book data ---------------------------------------
            book_results: list = readings_extractor.get_book_readings( class_id )
            ## ocra all-artcles data --------------------------------
            all_articles_results: list = readings_extractor.get_all_articles_readings( class_id )
            ## ocra filtered article data ---------------------------
            filtered_articles_results: dict = readings_processor.filter_article_table_results(all_articles_results)
            article_results = filtered_articles_results['article_results']
            audio_results = filtered_articles_results['audio_results']          # from article-table; TODO rename
            ebook_results = filtered_articles_results['ebook_results'] 
            excerpt_results = filtered_articles_results['excerpt_results']
            video_results = filtered_articles_results['video_results']          
            website_results = filtered_articles_results['website_results']      
            log.debug( f'website_results, ``{pprint.pformat(website_results)}``' )
            ## ocra tracks data -------------------------------------
            tracks_results: list = readings_extractor.get_tracks_data( class_id )
            ## ------------------------------------------------------
            ## MAP OCRA DATA TO LEGANTO DATA ------------------------           
            ## ------------------------------------------------------
            ## leganto article data ---------------------------------
            leg_articles: list = readings_processor.map_articles( article_results, course_id, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto audio data (from article-table) --------------
            leg_audios: list = readings_processor.map_audio_files( audio_results, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto book data ------------------------------------            
            leg_books: list = readings_processor.map_books( book_results, leganto_course_id, leganto_section_id, leganto_course_title, cdl_checker )
            ## leganto ebook data -----------------------------------
            leg_ebooks: list = readings_processor.map_ebooks( ebook_results, course_id, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto excerpt data ---------------------------------
            leg_excerpts: list = readings_processor.map_excerpts( excerpt_results, course_id, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto video data -----------------------------------
            leg_videos: list = readings_processor.map_videos( video_results, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto website data ---------------------------------
            leg_websites: list = readings_processor.map_websites( website_results, course_id, leganto_course_id, cdl_checker, leganto_section_id, leganto_course_title, settings )
            ## leganto tracks data ----------------------------------
            leg_tracks: list = readings_processor.map_tracks( tracks_results, course_id, leganto_course_id, leganto_section_id, leganto_course_title )
            ## leganto combined data --------------------------------
            # all_course_results: list = leg_articles + leg_books + leg_ebooks + leg_excerpts + leg_websites + leg_audios + leg_videos
            # all_course_results: list = leg_articles + leg_audios + leg_books + leg_ebooks + leg_excerpts + leg_videos + leg_websites  
            all_course_results: list = leg_articles + leg_audios + leg_books + leg_ebooks + leg_excerpts + leg_tracks + leg_videos + leg_websites  
            if all_course_results == []:
                all_course_results: list = [ readings_processor.map_empty(leganto_course_id, leganto_section_id, leganto_course_title) ]
        else:
            log.debug( f'no class_id found for class_info_entry, ``{class_info_entry}``' )
            all_course_results: list = [ readings_processor.map_empty(leganto_course_id, leganto_section_id, leganto_course_title) ]
        log.debug( f'all_course_results, ``{all_course_results}``' )
        all_results = all_results + all_course_results
        # log.debug( f'all_results, ``{pprint.pformat(all_results)}``' )
    log.info( f'all_results, ``{pprint.pformat(all_results)}``' )
    return all_results

    ## end def prep_basic_data()


def prep_leganto_data( basic_data: list, settings: dict ) -> list:
    """ Enhances basic data for spreadsheet and CSV-files. 
        Called by manage_build_reading_list() """
    leganto_data: list = []
    for entry in basic_data:
        log.debug( f'result-dict-entry, ``{pprint.pformat(entry)}``' )
        result: dict = entry
        row_dict = {}
        headers: list = leganto_final_processor.get_headers()
        for entry in headers:
            header: str = entry
            row_dict[header] = ''
        log.debug( f'default row_dict, ``{pprint.pformat(row_dict)}``' )
        course_code_found: bool = False if 'oit_course_code_not_found' in result['coursecode'] else True
        row_dict['citation_author'] = leganto_final_processor.clean_citation_author( result['citation_author'] ) 
        row_dict['citation_doi'] = result['citation_doi']
        row_dict['citation_end_page'] = result['citation_end_page']
        row_dict['citation_isbn'] = result['citation_isbn']
        row_dict['citation_issn'] = result['citation_issn']
        row_dict['citation_issue'] = result['citation_issue']
        row_dict['citation_journal_title'] = result['citation_journal_title']
        row_dict['citation_publication_date'] = result['citation_publication_date']
        row_dict['citation_public_note'] = 'Please contact rock-reserves@brown.edu if you have problem accessing the course-reserves material.' if result['external_system_id'] else ''
        row_dict['citation_secondary_type'] = leganto_final_processor.calculate_leganto_type( result['citation_secondary_type'] )
        row_dict['citation_source'] = leganto_final_processor.calculate_leganto_citation_source( result )
        row_dict['citation_start_page'] = result['citation_start_page']
        row_dict['citation_status'] = 'BeingPrepared' if result['external_system_id'] else ''
        row_dict['citation_title'] = leganto_final_processor.clean_citation_title( result['citation_title'] )
        row_dict['citation_volume'] = result['citation_volume']
        row_dict['coursecode'] = leganto_final_processor.calculate_leganto_course_code( result['coursecode'] )
        row_dict['reading_list_code'] = row_dict['coursecode'] if result['external_system_id'] else ''
        # row_dict['citation_library_note'] = leganto_final_processor.calculate_leganto_staff_note( result['citation_source1'], result['citation_source2'], result['citation_source3'], result['external_system_id'] )
        row_dict['citation_library_note'] = leganto_final_processor.calculate_leganto_staff_note( result['citation_source1'], result['citation_source2'], result['citation_source3'], result['external_system_id'], result.get('citation_library_note', '') )
        if row_dict['citation_library_note'] == 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND':
            result['external_system_id'] = 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND'  # so this will appear in the staff spreadsheet
        row_dict['reading_list_name'] = result['reading_list_name'] if result['external_system_id'] else ''
        row_dict['reading_list_status'] = 'BeingPrepared' if result['external_system_id'] else ''
        row_dict['section_id'] = result['section_id']
        row_dict['section_name'] = 'Resources' if result['external_system_id'] else ''
        row_dict['visibility'] = 'RESTRICTED' if result['external_system_id'] else ''
        log.debug( f'updated row_dict, ``{pprint.pformat(row_dict)}``' )
        leganto_data.append( row_dict )
    log.debug( f'leganto_data, ``{pprint.pformat(leganto_data)}``' )
    return leganto_data

    ## end def prep_leganto_data()


## -- script-caller helpers -----------------------------------------


def parse_args() -> dict:
    """ Parses arguments when module called via __main__ """
    log.debug( 'starting parse_args()' )
    # parser = argparse.ArgumentParser( description='Required: a `course_id` like `EDUC1234` (accepts multiples like `EDUC1234,HIST1234`) -- and confirmation that the spreadsheet should actually be updated with prepared data.' )
    parser = argparse.ArgumentParser( description='''Example usage...
    ## processes first 5 courses in oit_file ------------------------
    python3 ./build_reading_list.py -course_id oit_file -range_inclusive '{"start": 5, "end": 10}'
    ## processes two courses and updates the google-sheet -----------
    python3 ./build_reading_list.py -course_id EAST0402,TAPS1600 -update_ss true
    ## processes the google-sheet's worksheet-1 courses ------------- 
    python3 ./build_reading_list.py -course_id SPREADSHEET -update_ss true -force true 
    ''', 
        formatter_class=argparse.RawTextHelpFormatter )
    parser.add_argument( '-course_id', help='(required) typically like: `EDUC1234` -- or `SPREADSHEET` to get sources from google-sheet', required=True )
    parser.add_argument( '-update_ss', help='(required if course_id is `spreadsheet` or a course-listing) takes boolean `false` or `true`, used to specify whether spreadsheet should be updated with prepared data', required=False )
    parser.add_argument( '-force', help='(optional) takes boolean `false` or `true`, used to skip spreadsheet recently-updated check', required=False )
    parser.add_argument( '-range_inclusive', help='(optional) used only with `-course_id oit_file' )
    args: dict = vars( parser.parse_args() )
    log.info( f'\n\nSTARTING script; perceived args, ```{args}```' )
    ## do a bit of validation ---------------------------------------
    fail_check: bool = check_args( args )
    if fail_check == True:
        parser.print_help()
        sys.exit()
    return args


def check_args( args ) -> bool:
    """ Validates args.
        Called by parse_args() """
    log.debug( f'type(args), type(args)' )
    fail_check = False
    if args['course_id'] == None or len(args['course_id']) < 8:
        fail_check = True
    if args['course_id'] == 'oit_file' and args['range_inclusive']:
        ## check range_arg ------------------------------------------
        range_arg = {}
        try:
            range_arg = json.loads( args['range_inclusive'] )
        except:
            log.exception( 'json-load of `range_inclusive` failed' )
            fail_check = True
        try:
            assert range_arg['start'] <= range_arg['end']
        except:
            log.exception( 'range_inclusive arg validation failed' )
            fail_check = True
    if args['update_ss'] == None and args['course_id'] != 'oit_file':
        log.debug( 'update_ss must be specified if course_id is not `oit_file`' )
        fail_check = True
    if args['update_ss']:
        try: 
            json.loads( args['update_ss'] )
        except:
            log.exception( 'json-load of `update_ss` failed' )
            fail_check = True
    if args['force']:
        try:
            json.loads( args['force'] )
        except:
            log.exception( 'json-load of `force` failed' )
    log.debug( f'fail_check, ``{fail_check}``' )
    return fail_check

    ## end def check_args()


def update_range_arg( range_arg ) -> dict:
    """ Updates the start and end values to make the submitted "range_inclusive" argument work.
        Called by main() """
    log.debug( f'range_arg initially, ``{pprint.pformat(range_arg)}``' )
    updated_range_arg = range_arg.copy()
    original_start = range_arg['start']
    original_end = range_arg['end']

    if original_start == 1:
        updated_range_arg['start'] = 0      # don't return anything; this is the header
    else:
        updated_range_arg['start'] = original_start - 2

    if original_end == 1:
        updated_range_arg['end'] = 0        # don't return anything; this is the header
    else:
        updated_range_arg['end'] = original_end - 1

    log.debug( f'updated_range_arg, ``{pprint.pformat(updated_range_arg)}``' )
    return updated_range_arg


if __name__ == '__main__':
    log.debug( 'starting if()' )
    args: dict = parse_args()
    course_id: str  = args['course_id']
    if args['update_ss'] == None:
        update_ss = False
    else:
        update_ss: bool = json.loads( args['update_ss'] )
    force: bool = json.loads( args['force'] ) if args['force'] else False
    range_arg: dict = json.loads(args['range_inclusive']) if args['range_inclusive'] else {}
    # updated_range_arg = update_range_arg( range_arg )
    updated_range_arg = update_range_arg(range_arg) if range_arg else {}
    manage_build_reading_list( course_id, update_ss, force, updated_range_arg )
