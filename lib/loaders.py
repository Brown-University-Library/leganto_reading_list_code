import csv, datetime, json, logging, os, pathlib, pprint
from collections import OrderedDict


## logging ----------------------------------------------------------

LOG_PATH: str = os.environ['LGNT__LOG_PATH']

log_level_dict: dict = { 'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL }    
LOG_LEVEL: str = os.environ['LGNT__LOG_LEVEL']
log_level_value = log_level_dict[LOG_LEVEL]  # yields logging.DEBUG or logging.INFO, etc.
logging.basicConfig(
    filename=LOG_PATH,
    level=log_level_value,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S' )
log = logging.getLogger(__name__)


class OIT_Course_Loader( object ):

    def __init__(self, COURSES_FILEPATH: str) -> None:
        self.OIT_course_data: list = self.load_OIT_course_data( COURSES_FILEPATH )
        self.tracker: dict = { 
            'meta': {
                'total_oit_course_count': len(self.OIT_course_data),
                'processed_oit_course_count': 0,
            },
            'oit_courses_processed': {},
            'recent_course_data': {}
            }

    # def __init__(self, COURSES_FILEPATH: str) -> None:
    #     self.OIT_course_data: list = self.load_OIT_course_data( COURSES_FILEPATH )
    #     self.tracker: dict = { 
    #         'total_course_count': len(self.OIT_course_data),
    #         'oit_courses_processed': {},
    #         }

    def load_OIT_course_data( self, COURSES_FILEPATH: str ) -> list:
        """ On instantiation, loads courses CSV file into a list of dictionaries. """
        rows = []
        with open( COURSES_FILEPATH ) as f:
            reader = csv.DictReader( f, delimiter = '\t' )
            rows = list(reader)
        log.debug( f'first 2 rows, ``{pprint.pformat(rows[0:2])}``' )
        return rows

    def grab_course_list( self, range_arg: dict ) -> list:
        """ Returns a list of the OIT courses.
            Called by manage_build_reading_list -> prep_course_id_list(),
            ...when the script is run to specify getting the course-list from the OIT file.  """
        log.debug( f'range_arg, ``{range_arg}``' )
        course_codes: list = []
        for entry in self.OIT_course_data:
            course_entry: dict = entry
            oit_course_code = course_entry['COURSE_CODE']
            course_codes.append( oit_course_code )
        log.debug( f'course_codes total count, ``{len(course_codes)}``' )
        if range_arg:
            start = range_arg['start']
            end = range_arg['end']
            course_codes = course_codes[start:end]
        log.debug( f'course_codes retrieved count, ``{len(course_codes)}; partial, ``{pprint.pformat(course_codes[0:100])}````' )
        return course_codes

    def remove_already_processed_courses( self, oit_coursecode_list: list, settings: dict ) -> list:
        """ Removes courses already processed from the list, and updates the tracker.
            Called by manage_build_reading_list -> prep_course_id_list() """
        log.debug( f'oit_coursecode_list, ``{oit_coursecode_list}``' )
        updated_oit_coursecode_list: list = []
        ## load tracker-json ----------------------------------------
        processed_keys: list = []
        temp_tracker_data: dict = self.load_tracker_data( settings )
        try:
            processed_keys = list( temp_tracker_data['oit_courses_processed'].keys() )
        except:
            log.exception( 'problem loading tracker-data or getting oit_courses_processed keys' )
        log.debug( f'processed_keys, ``{processed_keys}``' )
        for oit_coursecode in oit_coursecode_list:
            log.debug( f'oit_coursecode, ``{oit_coursecode}``' )
            if oit_coursecode in processed_keys:
                log.debug( f'course already processed' )
                existing_file_tracker_coursecode_status = temp_tracker_data['oit_courses_processed'][oit_coursecode]['status']
                log.debug( f'existing_file_tracker_coursecode_status, ``{existing_file_tracker_coursecode_status}``' )
                # if 'NO-OCRA' in existing_file_tracker_coursecode_status:
                if existing_file_tracker_coursecode_status == 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND':
                    updated_status = 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND_already_processed'
                elif existing_file_tracker_coursecode_status =='NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND_already_processed':
                    updated_status = existing_file_tracker_coursecode_status
                else:
                    updated_status = 'already_processed'
                self.tracker['oit_courses_processed'][oit_coursecode] = {
                    'status': updated_status,
                    'datetime_stamp': datetime.datetime.now().isoformat()
                }
            else:
                log.debug( f'course not yet processed' )
                updated_oit_coursecode_list.append( oit_coursecode )
        log.debug( f'updated oit_coursecode_list, ``{oit_coursecode_list}``' )
        return updated_oit_coursecode_list

    def load_tracker_data( self, settings: dict ) -> dict:
        """ Loads tracker-data from json file.
            Called by remove_already_processed_courses() """
        tracker_data: dict = {}
        try:
            with open( settings['TRACKER_JSON_FILEPATH'], 'r' ) as f:
                tracker_data = json.loads( f.read() )
        except:
            log.exception( 'problem loading tracker-data; returning "{}"' )
        log.debug( f'tracker_data, ``{pprint.pformat(tracker_data)}``' )
        return tracker_data

    # def load_tracker_data( self, settings: dict ) -> dict:
    #     """ Loads tracker-data from json file.
    #         Called by remove_already_processed_courses() """
    #     tracker_data: dict = {}
    #     with open( settings['TRACKER_JSON_FILEPATH'], 'r' ) as f:
    #         try:
    #             tracker_data = json.loads( f.read() )
    #         except:
    #             log.exception( 'problem loading tracker-data; returning "{}"' )
    #     log.debug( f'tracker_data, ``{pprint.pformat(tracker_data)}``' )
    #     return tracker_data

    def populate_tracker( self, course_id_list: list ) -> None:
        """ Populates the tracker dict with the oit_course-id list. 
            Called by manage_build_reading_list -> prep_course_id_list() """
        for course_id in course_id_list:
            self.tracker['oit_courses_processed'][course_id] = {}
        log.debug( f'self.tracker, ``{pprint.pformat(self.tracker)}``' )
        return

    def convert_oit_course_code_to_plain_course_code( self, oit_course_code: str ) -> str:
        """ Returns the plain course-code.
            Called by manage_build_reading_list -> prep_classes_info() """
        # log.debug( f'oit_course_code, ``{oit_course_code}``' )
        parts: list = oit_course_code.split('.')
        try:
            plain_course_code: str = parts[1].upper() + parts[2].upper()
        except:
            log.exception( f'problem converting oit_course_code to plain_course_code for oit_course_code, ``{oit_course_code}``' )
            plain_course_code = ''
        return plain_course_code

    def grab_oit_course_data( self, coursecode: str ) -> list:
        """ Returns the OIT info for the simplistic-coursecode, _OR_ for the oit-coursecode.
            Called by manage_build_reading_list -> prep_classes_info() """
        log.debug( f'OIT_course_data - partial, ``{pprint.pformat(self.OIT_course_data)[0:1000]}...``' )
        log.debug( f'preparing oit-data for coursecode, ``{coursecode}``' )
        found_oit_course_data: list = []
        if '.' in coursecode:
            for entry in self.OIT_course_data:
                course_entry: dict = entry
                # log.debug( f'course_entry, ``{course_entry}``' )
                oit_course_code = course_entry['COURSE_CODE']
                if coursecode == oit_course_code:
                    found_oit_course_data.append( course_entry )
                    log.debug( 'match found; breaking' )
                    break
        else:
            for entry in self.OIT_course_data:
                course_entry: dict = entry
                # log.debug( f'course_entry, ``{course_entry}``' )
                oit_course_code = course_entry['COURSE_CODE']
                plain_course_code = self.convert_oit_course_code_to_plain_course_code( oit_course_code )
                if coursecode == plain_course_code:
                    found_oit_course_data.append( course_entry )
                    log.debug( f'found match on oit_course_code, ``{oit_course_code}``' )
        log.debug( f'found_oit_course_data, ``{found_oit_course_data}``' )
        return found_oit_course_data

    def update_tracker( self, leganto_data: list, settings: dict ) -> None:
        """ Updates the tracker dict with course-status.
            Called by manage_build_reading_list() """
        log.debug( f'self.tracker, ``{pprint.pformat(self.tracker)}``' )
        for entry in leganto_data:
            leganto_entry: dict = entry
            log.debug( f'leganto_entry, ``{leganto_entry}``' )
            oit_coursecode = leganto_entry['coursecode']
            # if leganto_entry['reading_list_library_note'] == 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND':
            if leganto_entry['citation_library_note'] == 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND':
                status: str = 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND'
            else:
                status: str = 'processed'
            self.tracker['oit_courses_processed'][oit_coursecode] = {
                'status': status,
                'datetime_stamp': datetime.datetime.now().isoformat(),
            }
        log.debug( f'self.tracker, ``{pprint.pformat(self.tracker)}``' )
        ## update tracker-json --------------------------------------
        self.write_tracker_data( leganto_data, settings )
        return

    # def update_tracker( self, leganto_data: list, settings: dict ) -> None:
    #     """ Updates the tracker dict with course-status.
    #         Called by manage_build_reading_list() """
    #     log.debug( f'self.tracker, ``{pprint.pformat(self.tracker)}``' )
    #     for entry in leganto_data:
    #         leganto_entry: dict = entry
    #         log.debug( f'leganto_entry, ``{leganto_entry}``' )
    #         oit_coursecode = leganto_entry['coursecode']
    #         if leganto_entry['reading_list_library_note'] == 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND':
    #             self.tracker['courses_to_process'][oit_coursecode]['status'] = 'NO-OCRA-BOOKS/ARTICLES/EXCERPTS-FOUND'
    #         else:
    #             self.tracker['courses_to_process'][oit_coursecode]['status'] = 'processed'
    #     log.debug( f'self.tracker, ``{pprint.pformat(self.tracker)}``' )
    #     ## update tracker-json --------------------------------------
    #     self.write_tracker_data( leganto_data, settings )
    #     return

    def write_tracker_data( self, leganto_data: list, settings: dict ) -> None:
        """ Updates the tracker json file.
            Called by update_tracker() """
        self.tracker['meta']['processed_oit_course_count'] = len( self.tracker['oit_courses_processed'] )
        if not os.path.isfile( settings['TRACKER_JSON_FILEPATH'] ):         # create file if it doesn't exist
            log.debug( 'creating tracker file' )
            with open( settings['TRACKER_JSON_FILEPATH'], 'w' ) as f:
                json.dump( self.tracker, f, sort_keys=True, indent=2 )
        else:
            log.debug( 'updating tracker file' )    
            with open( settings['TRACKER_JSON_FILEPATH'], 'r' ) as f:
                try:                                                        # try to read and update the file; could be empty
                    existing_tracker_data: dict = json.load( f )
                    log.debug( f'existing_tracker_data, ``{pprint.pformat(existing_tracker_data)}``' )  
                    for oit_coursecode in self.tracker['oit_courses_processed'].keys():
                        existing_tracker_data['oit_courses_processed'][oit_coursecode] = self.tracker['oit_courses_processed'][oit_coursecode]
                    log.debug( f'existing_tracker_data after update, ``{pprint.pformat(existing_tracker_data)}``' )  
                    existing_tracker_data['meta']['processed_oit_course_count'] = len( existing_tracker_data['oit_courses_processed'] )
                    with open( settings['TRACKER_JSON_FILEPATH'], 'w' ) as f:
                        json.dump( existing_tracker_data, f, sort_keys=True, indent=2 )    
                except:                                                     # if file is empty, just write the data
                    log.debug( 'tracker file is empty' )
                    with open( settings['TRACKER_JSON_FILEPATH'], 'w' ) as f:
                        json.dump( self.tracker, f, sort_keys=True, indent=2 )
        return

    ## end class OIT_Course_Loader()


def rebuild_pdf_data_if_necessary( days: dict ) -> dict:
    """ Initiates OCRA pdf-data extraction if necessary. 
        Called by build_reading_list.manage_build_reading_list() """
    log.debug( f'days, ``{days}``' )
    num_days: int = days['days']
    return_val = {}
    PDF_JSON_PATH: str = os.environ['LGNT__PDF_JSON_PATH']
    log.debug( f'PDF_JSON_PATH, ``{PDF_JSON_PATH}``' )
    update: bool = determine_update( num_days, PDF_JSON_PATH, datetime.datetime.now()  )
    if update:
        log.debug( 'gonna update the pdf-data -- TODO' )
        try:
            from lib import make_pdf_json_data  # the import actually runs the code
        except Exception as e:
            log.exception( 'problem running pdf-json script' )
            return_val = { 'err': repr(e) }
    else:
        log.debug( 'pdf_data is new enough; not updating' )
    return return_val


def determine_update( days: int, fpath: str, now_time: datetime.datetime ) -> bool:
    """ Determines whether to update given file. 
        Called by rebuild_pdf_data_if_necessary() """
    log.debug( f'days, ``{days}``' )
    log.debug( f'now_time, ``{now_time}``' )
    return_val = False
    last_updated_epoch_timestamp: float = pathlib.Path( fpath ).stat().st_mtime
    dt_last_updated: datetime.datetime = datetime.datetime.fromtimestamp( last_updated_epoch_timestamp )
    cutoff_date: datetime.datetime = dt_last_updated + datetime.timedelta( days )
    log.debug( f'cutoff_date, ``{str(cutoff_date)}``' )
    if cutoff_date < now_time:
        return_val = True
    log.debug( f'return_val, ``{return_val}``' )
    return return_val
