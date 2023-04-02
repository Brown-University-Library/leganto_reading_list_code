"""
- This script produces reading-list files for each course in "json_data/oit_data_04.json".
- The necessary leganto categories are defined.
- Data is prepared from the OCRA data, with some additional lookups.
    - TODO: Define the addtional lookups.
"""

import datetime, json, logging, os, pprint, sys

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

## additional imports -----------------------------------------------
from lib import leganto_final_processor

## grab env vars ----------------------------------------------------
JSON_DATA_DIR_PATH: str = os.environ['LGNT__JSON_DATA_DIR_PATH']
CSV_DATA_DIR_PATH: str = os.environ['LGNT__CSV_OUTPUT_DIR_PATH']
log.debug( f'JSON_DATA_DIR_PATH, ``{JSON_DATA_DIR_PATH}``' )
log.debug( f'CSV_DATA_DIR_PATH, ``{CSV_DATA_DIR_PATH}``' )

## globals ----------------------------------------------------------
JSON_DATA_SOURCE_PATH = f'{JSON_DATA_DIR_PATH}/oit_data_04.json'
datetimestamp = datetime.datetime.now().isoformat().replace( ':', '-' )[0:22]  # two decimal places is enough
TSV_DATA_OUTPUT_PATH = f'{CSV_DATA_DIR_PATH}/2023_summer/list_{datetimestamp}.tsv'
log.debug( f'JSON_DATA_SOURCE_PATH, ``{JSON_DATA_SOURCE_PATH}``' )
log.debug( f'TSV_DATA_OUTPUT_PATH, ``{TSV_DATA_OUTPUT_PATH}``' )


## controller -------------------------------------------------------

def main():
    """ Controller.
        Called by if __name__ == '__main__' """
    
    ## load source file ---------------------------------------------
    data_holder_dict = {}
    with open( JSON_DATA_SOURCE_PATH, 'r' ) as f:
        data_holder_dict = json.loads( f.read() )

    ## initialize meta ----------------------------------------------
    meta = {
        'datetime_stamp': datetime.datetime.now().isoformat(),
        'description': f'Starts with "oit_data_04.json". Produces "{TSV_DATA_OUTPUT_PATH}" file. Defines necessary leganto fields and assembles the data. Then writes it to a .tsv file.',
        'number_of_courses_in_reading_list_file': len( data_holder_dict ) - 1, # -1 for meta
        'number_of_courses_below': 0,
        }
    
    ## initialize leganto fields ------------------------------------
    reading_list_lines = []
    leganto_dict_template = {}
    leganto_list_header_dict = {}
    leganto_fields = leganto_final_processor.get_headers()
    for field in leganto_fields:
        leganto_dict_template[field] = ''
        leganto_list_header_dict[field] = field
    reading_list_lines.append( leganto_list_header_dict )
    # log.debug( f'reading_list_lines, ``{pprint.pformat(reading_list_lines, sort_dicts=False)}``' )
    
    ## process courses ----------------------------------------------
    for ( i, (course_key, course_data_dict) ) in enumerate( data_holder_dict.items() ):
        if course_key == '__meta__':
            continue

        log.debug( f'processing course_key, ``{course_key}``')
        log.debug( f'course_data_dict, ``{pprint.pformat(course_data_dict)}``')

        leganto_dct = leganto_dict_template.copy()
        leganto_dct['coursecode'] = course_data_dict['oit_course_id']
        log.debug( f'leganto_dct, ``{pprint.pformat(leganto_dct, sort_dicts=False)}``' )

        ## add to reading_list_lines --------------------------------
        reading_list_lines.append( leganto_dct )
        log.debug( f'reading_list_lines, ``{pprint.pformat(reading_list_lines, sort_dicts=False)}``' )

        1/0

        ## add basic course data to new data-holder -----------------
        basic_course_data = {
            'ocra_class_id_to_instructor_email_map_for_matches': course_data_dict['ocra_class_id_to_instructor_email_map_for_matches'],
            'oit_bruid_to_email_map': course_data_dict['oit_bruid_to_email_map'],
            'oit_course_id': course_data_dict['oit_course_id'],
            'oit_course_title': course_data_dict['oit_course_title'],
            'status': 'not_yet_processed',
        }
        updated_data_holder_dict[course_key] = basic_course_data
        ## switch to new data-holder --------------------------------
        course_data_dict = updated_data_holder_dict[course_key]
        ## add inverted email-match map -----------------------------
        existing_classid_to_email_map = course_data_dict['ocra_class_id_to_instructor_email_map_for_matches']
        inverted_ocra_classid_email_map = make_inverted_ocra_classid_email_map( existing_classid_to_email_map )
        course_data_dict['inverted_ocra_classid_email_map'] = inverted_ocra_classid_email_map
        log.debug( f'course_data_dict, ``{pprint.pformat(course_data_dict)}``' )
        ## get class_ids --------------------------------------------
        relevant_course_classids = inverted_ocra_classid_email_map.values()
        log.debug( f'relevant_course_classids, ``{pprint.pformat(relevant_course_classids)}``' )

        ## process relevant class_ids ------------------------------------
        all_course_results = {}
        for class_id in relevant_course_classids:
            ## ------------------------------------------------------
            ## GET OCRA DATA ----------------------------------------
            ## ------------------------------------------------------            
            ## ocra book data -------------------------------------------
            book_results: list = readings_extractor.get_book_readings( class_id )
            if book_results:
                for book_result in book_results:
                    if book_result['bk_updated']:
                        book_result['bk_updated'] = book_result['bk_updated'].isoformat()
                    if book_result['request_date']:
                        book_result['request_date'] = book_result['request_date'].isoformat()
                    if book_result['needed_by']:
                        book_result['needed_by'] = book_result['needed_by'].isoformat()
                    if book_result['date_printed']:
                        book_result['date_printed'] = book_result['date_printed'].isoformat()
            ## ocra all-artcles data ------------------------------------
            all_articles_results: list = readings_extractor.get_all_articles_readings( class_id )
            ## ocra filtered article data -------------------------------
            filtered_articles_results: dict = filter_article_table_results(all_articles_results)
            for type_key, result_value in filtered_articles_results.items():
                if result_value:
                    for result in result_value:
                        if result['art_updated']:
                            result['art_updated'] = result['art_updated'].isoformat()
                        if result['date']:
                            result['date'] = result['date'].isoformat()
                        if result['date_due']:
                            result['date_due'] = result['date_due'].isoformat()
                        if result['request_date']:
                            result['request_date'] = result['request_date'].isoformat()
                        if result['date_printed']:
                            result['date_printed'] = result['date_printed'].isoformat()
            article_results = filtered_articles_results['article_results']
            audio_results = filtered_articles_results['audio_results']          # from article-table; TODO rename
            ebook_results = filtered_articles_results['ebook_results'] 
            excerpt_results = filtered_articles_results['excerpt_results']
            video_results = filtered_articles_results['video_results']          
            website_results = filtered_articles_results['website_results']      
            # log.debug( f'website_results, ``{pprint.pformat(website_results)}``' )
            ## ocra tracks data -----------------------------------------
            tracks_results: list = readings_extractor.get_tracks_data( class_id )                

            ## combine results ------------------------------------------
            classid_results = {
                'book_results': book_results,
                'article_results': article_results,
                'audio_results': audio_results,
                'ebook_results': ebook_results,
                'excerpt_results': excerpt_results,
                'video_results': video_results,
                'website_results': website_results,
                'tracks_results': tracks_results,
            }
            all_course_results[class_id] = classid_results

            ## end for-class_id loop...

        course_data_dict['ocra_course_data'] = all_course_results
        ocra_data_found_check = check_for_ocra_data( all_course_results )
        if ocra_data_found_check == False:
            meta['courses_with_no_ocra_data'].append( course_key )
        course_data_dict['status'] = 'processed'

        # if i > 2:
        #     break

    ## end for-course loop...

    ## delete no-ocra-match courses ---------------------------------
    for course_key in meta['courses_with_no_ocra_data']:
        del updated_data_holder_dict[course_key]
    meta['number_of_courses_below'] = len( updated_data_holder_dict ) - 1 # -1 for meta

    log.debug( f'updated_data_holder_dict, ``{pprint.pformat(updated_data_holder_dict)}``' )

    ## save ---------------------------------------------------------
    with open( JSON_DATA_OUTPUT_PATH, 'w' ) as f:
        try:
            jsn = json.dumps( updated_data_holder_dict, sort_keys=True, indent=2 )
        except Exception as e:
            message = f'problem with json.dumps(); e, ``{e}``'
            log.exception( message )
            raise Exception( message )
        f.write( jsn )

    return

    ## end main()


## helper functions ---------------------------------------------


def make_inverted_ocra_classid_email_map( existing_classid_to_email_map ) -> dict:
    """ Converts `existing_classid_to_email_map` to `inverted_ocra_classid_email_map
        Takes a dict like:
            {   '10638': 'person_A@brown.edu',
                '8271': 'person_A@brown.edu',
                '8500': 'person_B@brown.edu'
                '8845': 'person_A@brown.edu' }
        ...and returns a dict like:
            {   'person_A@brown.edu': '10638',
                'person_B@brown.edu': '8500'  }
        Allows for multiple class_ids per email, and returns the highest (latest) class_id. 
        Called by main() """
    ## convert keys to integers and sort them -----------------------
    int_keys = sorted( [int(key) for key in existing_classid_to_email_map.keys()] )
    temp_int_dict = {}
    for key in int_keys:
        temp_int_dict[key] = existing_classid_to_email_map[str(key)]
    inverted_ocra_classid_email_map = {}
    for ( class_id_key, email_val ) in temp_int_dict.items():
        inverted_ocra_classid_email_map[email_val] = str( class_id_key )
    log.debug( f'inverted_ocra_classid_email_map, ``{pprint.pformat(inverted_ocra_classid_email_map)}``' )
    return inverted_ocra_classid_email_map


def filter_article_table_results( all_articles_results ):
    """ Takes all article results and puts them in proper buckets.
        Called by main() """
    assert type(all_articles_results) == list
    log.debug( f'count of all_articles_results, ``{len(all_articles_results)}``' )
    ( article_results, audio_results, ebook_results, excerpt_results, video_results, website_results ) = ( [], [], [], [], [], [] )
    for result in all_articles_results:
        if 'format' in result.keys():
            if result['format'].strip() == 'article':
                article_results.append( result )
            elif result['format'].strip() == 'audio':
                audio_results.append( result )
            elif result['format'].strip() == 'ebook':
                ebook_results.append( result )
            elif result['format'].strip() == 'excerpt':
                excerpt_results.append( result )
            elif result['format'].strip() == 'video':
                video_results.append( result )
            elif result['format'].strip() == 'website':
                website_results.append( result )
            else:
                log.debug( f'unknown format, ``{result["format"]}``' )
        else:   # no format
            log.debug( f'no format, ``{result}``' )
    log.debug( f'count of article_results, ``{len(article_results)}``' )
    log.debug( f'count of audio_results, ``{len(audio_results)}``' )
    log.debug( f'count of ebook_results, ``{len(ebook_results)}``' )
    log.debug( f'count of excerpt_results, ``{len(excerpt_results)}``' )
    log.debug( f'count of video_results, ``{len(video_results)}``' )
    log.debug( f'count of website_results, ``{len(website_results)}``' )
    filtered_results = {
        'article_results': article_results,
        'audio_results': audio_results,
        'ebook_results': ebook_results,
        'excerpt_results': excerpt_results,
        'video_results': video_results,
        'website_results': website_results }    
    # log.debug( f'filtered_results, ``{pprint.pformat(filtered_results)}``' )
    return filtered_results  

    ## end def filter_article_table_results()  


def check_for_ocra_data( all_course_results ):
    """ Checks if there's any ocra data in the course_results.
        all_course_results is a dict like:
            { '1234': 
                {'article_results': [], 'book_results: [], etc...},
              '2468': 
                {'article_results': [], 'book_results: [], etc...},
            }
        Called by main() """
    ocra_data_found_check = False
    for ( class_id, classid_results ) in all_course_results.items():
        for ( format, format_results ) in classid_results.items():
            if len(format_results) > 0:
                ocra_data_found_check = True
    log.debug( f'ocra_data_found_check, ``{ocra_data_found_check}``' )
    return ocra_data_found_check


if __name__ == '__main__':
    main()
    sys.exit()