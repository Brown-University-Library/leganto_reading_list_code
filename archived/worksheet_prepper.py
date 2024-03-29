# """
# Archived.
# - replaced by lib/gsheet_prepper.py and other code in refactor
#     to separate data-prep from worksheet display.
# """

# import datetime, logging, os, pprint

# import gspread


# log = logging.getLogger(__name__)

# headers = [
#     'coursecode', 'section_id', 'searchable_id1', 'searchable_id2', 'searchable_id3', 'reading_list_code', 
#     'reading_list_name', 'reading_list_description', 'reading_list_subject', 'reading_list_status', 'RLStatus', 
#     'visibility', 'reading_list_assigned_to', 'reading_list_library_note', 'reading_list_instructor_note', 
#     'owner_user_name', 'creati vecommon', 'section_name', 'section_description', 'section_start_date', 
#     'section_end_date', 'section_tags', 'citation_secondary_type', 'citation_status', 'citation_tags', 
#     'citation_mms_id', 'citation_original_system_id', 'citation_title', 'citation_journal_title', 'citation_author', 
#     'citation_publication_date', 'citation_edition', 'citation_isbn', 'citation_issn', 
#     'citation_place_of_publication', 'citation_publisher', 'citation_volume', 'citation_issue', 'citation_pages', 
#     'citation_start_page', 'citation_end_page', 'citation_doi', 'citation_oclc', 'citation_lccn', 
#     'citation_chapter', 'rlterms_chapter_title', 'citation_chapter_author', 'editor', 'citation_source', 
#     'citation_source1', 'citation_source2', 'citation_source3', 'citation_source4', 'citation_source5', 
#     'citation_source6', 'citation_source7', 'citation_source8', 'citation_source9', 'citation_source10', 
#     'citation_note', 'additional_person_name', 'file_name', 'citation_public_note', 'license_type', 
#     'citation_instructor_note', 'citation_library_note', 'external_system_id'
# ]


# ## 3 main manager/worker functions ----------------------------------


# def update_gsheet( all_results: list, CREDENTIALS: dict, SPREADSHEET_NAME: str ) -> dict:
#     """ Writes data to gsheet, then...
#         - sorts the worksheets so the most recent check appears first in the worksheet list.
#         - deletes checks older than the curent and previous checks.
#         Called by check_bibs() """
#     ## access spreadsheet -------------------------------------------
#     log.debug( f'all_results, ``{pprint.pformat(all_results)}``' )
#     credentialed_connection = gspread.service_account_from_dict( CREDENTIALS )
#     sheet = credentialed_connection.open( SPREADSHEET_NAME )
#     log.debug( f'last-updated, ``{sheet.lastUpdateTime}``' )  # not needed now, but will use it later
#     ## process leganto worksheet ------------------------------------
#     leganto_data: list = process_leganto_worksheet( sheet, all_results )
#     ## process staff worksheet --------------------------------------
#     process_staff_worksheet( sheet, all_results )
#     return_val: dict = {'leganto_data': leganto_data}
#     return return_val


# def process_leganto_worksheet( sheet, all_results: list ) -> list:
#     ## create leganto worksheet -------------------------------------
#     dt_stamp: str = datetime.datetime.now().isoformat().split( '.' )[0]
#     title: str = f'for_leganto_{dt_stamp}'
#     leganto_worksheet = sheet.add_worksheet( title=title, rows=100, cols=20 )
#     ## prepare headers ----------------------------------------------
#     # headers = [
#     #     'coursecode', 'section_id', 'searchable_id1', 'searchable_id2', 'searchable_id3', 'reading_list_code', 
#     #     'reading_list_name', 'reading_list_description', 'reading_list_subject', 'reading_list_status', 'RLStatus', 
#     #     'visibility', 'reading_list_assigned_to', 'reading_list_library_note', 'reading_list_instructor_note', 
#     #     'owner_user_name', 'creativecommon', 'section_name', 'section_description', 'section_start_date', 
#     #     'section_end_date', 'section_tags', 'citation_secondary_type', 'citation_status', 'citation_tags', 
#     #     'citation_mms_id', 'citation_original_system_id', 'citation_title', 'citation_journal_title', 'citation_author', 
#     #     'citation_publication_date', 'citation_edition', 'citation_isbn', 'citation_issn', 
#     #     'citation_place_of_publication', 'citation_publisher', 'citation_volume', 'citation_issue', 'citation_pages', 
#     #     'citation_start_page', 'citation_end_page', 'citation_doi', 'citation_oclc', 'citation_lccn', 
#     #     'citation_chapter', 'rlterms_chapter_title', 'citation_chapter_author', 'editor', 'citation_source', 
#     #     'citation_source1', 'citation_source2', 'citation_source3', 'citation_source4', 'citation_source5', 
#     #     'citation_source6', 'citation_source7', 'citation_source8', 'citation_source9', 'citation_source10', 
#     #     'citation_note', 'additional_person_name', 'file_name', 'citation_public_note', 'license_type', 
#     #     'citation_instructor_note', 'citation_library_note', 'external_system_id'
#     # ]
#     log.debug( f'headers, ``{headers}``' )
#     ## prepare values -----------------------------------------------
#     data_values = []  # for gsheet
#     csv_rows = []     # for csv output
#     # row_dict = {}
#     # for header in headers:
#     #     header: str = header
#     #     row_dict[header] = ''
#     # log.debug( f'default row_dict, ``{pprint.pformat(row_dict)}``' )
#     for result in all_results:
#         log.debug( f'result-dict-entry, ``{pprint.pformat(result)}``' )
#         result: dict = result

#         row_dict = {}
#         for header in headers:
#             header: str = header
#             row_dict[header] = ''
#         log.debug( f'default row_dict, ``{pprint.pformat(row_dict)}``' )
        
#         course_code_found: bool = False if 'oit_course_code_not_found' in result['coursecode'] else True

#         # row_dict['citation_author'] = result['citation_author']
#         row_dict['citation_author'] = clean_citation_author( result['citation_author'] ) 
#         row_dict['citation_doi'] = result['citation_doi']
#         row_dict['citation_end_page'] = result['citation_end_page']
#         row_dict['citation_isbn'] = result['citation_isbn']
#         row_dict['citation_issn'] = result['citation_issn']
#         row_dict['citation_issue'] = result['citation_issue']
#         row_dict['citation_journal_title'] = result['citation_journal_title']
#         row_dict['citation_publication_date'] = result['citation_publication_date']
#         row_dict['citation_public_note'] = 'Please contact rock-reserves@brown.edu if you have problem accessing the course-reserves material.' if result['external_system_id'] else ''
#         row_dict['citation_secondary_type'] = calculate_leganto_type( result['citation_secondary_type'] )
#         row_dict['citation_source'] = calculate_leganto_citation_source( result )
#         row_dict['citation_start_page'] = result['citation_start_page']
#         row_dict['citation_status'] = 'BeingPrepared' if result['external_system_id'] else ''
#         # row_dict['citation_title'] = calculate_leganto_title( result['citation_title'] )
#         row_dict['citation_title'] = clean_citation_title( result['citation_title'] )
#         row_dict['citation_volume'] = result['citation_volume']
#         row_dict['coursecode'] = calculate_leganto_course_code( result['coursecode'] )
#         row_dict['reading_list_code'] = row_dict['coursecode'] if result['external_system_id'] else ''
#         # row_dict['reading_list_library_note'] = f'Possible full-text link: <{result["citation_source2"]}>.' if result["citation_source2"] else ''
#         # row_dict['reading_list_library_note'] = f'Possible full-text link: <https://url_one>./nOccasionally-helpful link: <https://url_two>'
#         row_dict['reading_list_library_note'] = calculate_leganto_staff_note( result['citation_source2'], result['citation_source3'] )
#         row_dict['reading_list_name'] = result['reading_list_name'] if result['external_system_id'] else ''
#         row_dict['reading_list_status'] = 'BeingPrepared' if result['external_system_id'] else ''
#         # row_dict['section_id'] = result['section_id']
#         row_dict['section_id'] = result['section_id'] if result['external_system_id'] else 'NO-OCRA-DATA-FOUND'
#         row_dict['section_name'] = 'Resources' if result['external_system_id'] else ''
#         row_dict['visibility'] = 'RESTRICTED' if result['external_system_id'] else ''
#         log.debug( f'updated row_dict, ``{pprint.pformat(row_dict)}``' )
#         csv_rows.append( row_dict )
#         row_values: list = list( row_dict.values() )
#         data_values.append( row_values )
#     log.debug( f'csv_rows, ``{pprint.pformat(csv_rows)}``' )
#     log.debug( f'data_values, ``{data_values}``' )
#     ## finalize leganto data ----------------------------------------
#     end_range_column = calculate_end_column( len(headers) )
#     num_entries = len( all_results )
#     data_end_range: str = f'{end_range_column}{num_entries + 1}'  # the plus-1 is for the header-row
#     log.debug( f'data_end_range, ``{data_end_range}``' )
#     new_data = [
#         { 
#             'range': f'A1:{end_range_column}1',
#             'values': [ headers ]
#         },
#         {
#             'range': f'A2:{data_end_range}',
#             'values': data_values
#         }
#     ]
#     leganto_worksheet.batch_update( new_data, value_input_option='raw' )
#     ## update leganto-sheet formatting ------------------------------
#     leganto_worksheet.format( f'A1:{end_range_column}1', {'textFormat': {'bold': True}} )
#     # leganto_worksheet.freeze( rows=1, cols=None )
#     leganto_worksheet.freeze( rows=1, cols=2 )
#     ## make leganto-sheet the 2nd sheet -----------------------------
#     wrkshts: list = sheet.worksheets()
#     log.debug( f'wrkshts, ``{wrkshts}``' )
#     reordered_wrkshts: list = [ wrkshts[0], wrkshts[-1] ]
#     sheet.reorder_worksheets( reordered_wrkshts )
#     wrkshts: list = sheet.worksheets()
#     log.debug( f'wrkshts after sort, ``{wrkshts}``' )
#     num_wrkshts: int = len( wrkshts )
#     log.debug( f'num_wrkshts, ``{num_wrkshts}``' )
#     if num_wrkshts > 2:  # keep requested_checks, and the leganto sheet
#         wrkshts: list = sheet.worksheets()
#         wrkshts_to_delete = wrkshts[2:]
#         for wrksht in wrkshts_to_delete:
#             sheet.del_worksheet( wrksht )
#     wrkshts: list = sheet.worksheets()
#     log.debug( f'wrkshts after deletion, ``{wrkshts}``' )
#     return csv_rows

#     # end def process_leganto_worksheet()


# def process_staff_worksheet( sheet, all_results: list ):
#     ## create staff worksheet -------------------------------------
#     dt_stamp: str = datetime.datetime.now().isoformat().split( '.' )[0]
#     title: str = f'for_staff_{dt_stamp}'
#     staff_worksheet = sheet.add_worksheet( title=title, rows=100, cols=20 )
#     ## prepare headers ----------------------------------------------
#     headers = [
#         'coursecode',
#         'section_id',
#         'citation_secondary_type',
#         'citation_title',
#         'citation_journal_title',
#         'citation_author',
#         'citation_publication_date',
#         'citation_doi',
#         'citation_isbn',
#         'citation_issn',
#         'citation_volume',
#         'citation_issue',
#         'citation_start_page',
#         'citation_end_page',
#         'citation_source1',
#         'citation_source2',
#         'citation_source3',
#         'citation_source4',
#         'external_system_id'
#         ]
#     ## prepare values -----------------------------------------------
#     data_values = []
#     for entry in all_results:
#         entry: dict = entry
#         row = [
#             entry['coursecode'],
#             entry['section_id'],
#             entry['citation_secondary_type'],
#             entry['citation_title'],
#             entry['citation_journal_title'],
#             entry['citation_author'],
#             entry['citation_publication_date'],
#             entry['citation_doi'],
#             entry['citation_isbn'],
#             entry['citation_issn'],
#             entry['citation_volume'],
#             entry['citation_issue'],
#             entry['citation_start_page'],
#             entry['citation_end_page'],
#             entry['citation_source1'],
#             entry['citation_source2'],
#             entry['citation_source3'],
#             entry['citation_source4'],
#             entry['external_system_id']
#             ]
#         data_values.append( row )
#     log.debug( f'data_values, ``{data_values}``' )
#     ## finalize staff data ----------------------------------------
#     end_range_column = 'S'
#     header_end_range = 'S1'
#     num_entries = len( all_results )
#     data_end_range: str = f'{end_range_column}{num_entries + 1}'  # the plus-1 is for the header-row
#     log.debug( f'data_end_range, ``{data_end_range}``' )
#     new_data = [
#         { 
#             'range': f'A1:{header_end_range}',
#             'values': [ headers ]
#         },
#         {
#             'range': f'A2:{data_end_range}',
#             'values': data_values
#         }
#     ]
#     log.debug( f'new_data, ``{pprint.pformat(new_data)}``' )
#     staff_worksheet.batch_update( new_data, value_input_option='raw' )
#     ## update staff-sheet formatting --------------------------------------------
#     staff_worksheet.format( f'A1:{end_range_column}1', {'textFormat': {'bold': True}} )
#     staff_worksheet.freeze( rows=1, cols=1 )
#     ## (no need to sort sheets here)
#     return

#     # end def process_staff_worksheet()


# ## helpers ----------------------------------------------------------


# def clean_citation_title( db_title: str ) -> str:
#     log.debug( f'db_title initially, ``{db_title}``' )
#     if db_title:
#         db_title = db_title.strip()
#         if '(EXCERPT)' in db_title:
#             db_title = db_title.replace( '(EXCERPT)', '' )
#         db_title = db_title.strip()
#         if db_title[-1] == ':':
#             db_title = db_title[0:-1]
#         if db_title[-1] == '.':
#             log.debug( 'found period' )
#             db_title = db_title[0:-1]
#         if db_title[0] == '“':  # starting smart-quotes
#             ## remove initial-smart-quotes if there's only one, and only one end-smart-quotes, and it's at the end.
#             log.debug( 'found starting smart-quotes' )
#             count_start: int = db_title.count( '“' )
#             if count_start == 1:
#                 count_end: int = db_title.count( '”' )
#                 if count_end == 1:
#                     if db_title[-1] == '”':  # ok, remove both
#                         db_title = db_title[1:-1]
#         if db_title[0] == '“':
#             count_quotes: int = db_title.count( '“' )
#             if count_quotes == 1:
#                 db_title = db_title[1:] 
#         if db_title[0] == '"':
#             ## remove initial-quotes if there are two, and the other is at the end.
#             log.debug( 'found starting simple-quotes' )
#             count_quotes: int = db_title.count( '"' )
#             if count_quotes == 2:
#                 if db_title[-1] == '"':  # ok, remove both
#                     db_title = db_title[1:-1]
#         if db_title[0] == '"':
#             count_quotes: int = db_title.count( '"' )
#             if count_quotes == 1:
#                 db_title = db_title[1:]
#         db_title = db_title.strip()
#     log.debug( f'db_title cleaned, ``{db_title}``' )
#     return db_title


# def clean_citation_author( db_author: str ) -> str:
#     log.debug( f'db_author initially, ``{db_author}``' )
#     if db_author:
#         db_author = db_author.strip()
#         if db_author[0] == ',':
#             db_author = db_author[1:]
#         if db_author[-1] == ',':
#             db_author = db_author[0:-1]
#         db_author = db_author.strip()
#     log.debug( f'db_author cleaned, ``{db_author}``' )
#     return db_author


# def calculate_end_column( number_of_columns: int ) -> str:
#     """ Calculates end-column string from number-of-columns. """
#     alphabet: list = list( 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' )
#     result = ''
#     if number_of_columns <= 26:
#         zero_length = number_of_columns - 1
#         result: str = alphabet[zero_length]
#     else:
#         ( multiple, remainder ) = divmod( number_of_columns, 26 )
#         log.debug( f'multiple, ``{multiple}``; remainder, ``{remainder}``' )
#         zero_multiple: int = multiple - 1
#         zero_remainder: int = remainder - 1
#         char_one: str = alphabet[zero_multiple]
#         char_two: str = alphabet[zero_remainder]
#         result = f'{char_one}{char_two}'
#     log.debug( f'result, ``{result}``' )
#     return result


# # def calculate_leganto_title( title: str ) -> str:
# #     """ Removes `(EXCERPT) ` if necessary. """
# #     return_title = title
# #     if '(EXCERPT)' in title:
# #         return_title = title.replace( '(EXCERPT)', '' )
# #         return_title = return_title.strip()
# #     log.debug( f'return_title, ``{return_title}``' )
# #     return return_title


# def calculate_leganto_type( perceived_type: str ) -> str:
#     """ Converts `ARTICLE` to `JR` """
#     return_type = perceived_type
#     if perceived_type == 'ARTICLE':
#         return_type = 'JR'
#     log.debug( f'return_type, ``{return_type}``' )
#     return return_type


# def calculate_leganto_course_code( data_string: str ) -> str:
#     """ Removes commentary if necessary. """
#     calculated_course_code = data_string
#     if 'oit_course_code_not_found' in data_string:
#         calculated_course_code = ''
#     log.debug( f'calculated_course_code, ``{calculated_course_code}``' )
#     return calculated_course_code


# def calculate_leganto_citation_source( result: dict ) -> str:
#     """ Prioritizes PDF, then CDL. """
#     link: str = ''
#     possible_pdf_data: str = result['citation_source4']
#     possible_cdl_data: str = result['citation_source1']
#     if possible_pdf_data:
#         log.debug( f'in `possible_pdf_data`; possible_pdf_data, ``{possible_pdf_data}``')
#         if possible_pdf_data == 'no_pdf_found':
#             link = ''
#         else:
#             link = possible_pdf_data
#     elif possible_cdl_data:
#         log.debug( f'in `possible_cdl_data`; possible_cdl_data, ``{possible_cdl_data}``')
#         if possible_cdl_data == 'TODO -- handle multiple possible results':
#             link = ''
#         elif possible_cdl_data == 'no CDL link found':
#             link = ''
#         elif 'CDL link' in possible_cdl_data:
#             # log.debug( 'here' )
#             link = possible_cdl_data.replace( 'CDL link likely: <', '' )
#             link = link.replace( 'CDL link possibly: <', '' )
#             link = link.replace( '>', '' )
#         else:
#             link = possible_cdl_data
#     log.debug( f'link, ``{link}``' )
#     return link


# def calculate_leganto_staff_note( possible_full_text: str, possible_openurl: str ) -> str:
#     """ Returns possibly-helpful info for staff. """
#     log.debug( f'possible_full_text, ``{possible_full_text}``' )
#     log.debug( f'possible_openurl, ``{possible_openurl}``' )
#     message = ''
#     if possible_full_text:
#         message = f'Possible full-text link: <{possible_full_text}>.'
#     if possible_openurl:
#         if 'https' in possible_openurl:
#             params: str = possible_openurl.split( 'openurl?' )[1]  # sometimes there's a link, but with no parameters.
#             if params:
#                 log.debug( 'params exist' )
#                 ourl_message: str = f'Occasionally-helpful link: <{possible_openurl}>.'
#                 if message:
#                     message = f'{message} {ourl_message}'
#                 else:
#                     message = ourl_message
#     log.debug( f'staff-message, ``{message}``' )
#     return message


# ## old code below, for reference 'til 2023-Jan-01

# # def update_gsheet( all_results: list ) -> None:
# #     """ Writes data to gsheet, then...
# #         - sorts the worksheets so the most recent check appears first in the worksheet list.
# #         - deletes checks older than the curent and previous checks.
# #         Called by check_bibs() """
# #     ## access spreadsheet -------------------------------------------
# #     log.debug( f'all_results, ``{pprint.pformat(all_results)}``' )
# #     credentialed_connection = gspread.service_account_from_dict( CREDENTIALS )
# #     sheet = credentialed_connection.open( SPREADSHEET_NAME )
# #     log.debug( f'last-updated, ``{sheet.lastUpdateTime}``' )  # not needed now, but will use it later
# #     ## create new worksheet ----------------------------------------
# #     title: str = f'check_results_{datetime.datetime.now()}'
# #     worksheet = sheet.add_worksheet(
# #         title=title, rows=100, cols=20
# #         )
# #     ## prepare range ------------------------------------------------
# #     headers = [
# #         'coursecode',
# #         'section_id',
# #         'citation_secondary_type',
# #         'citation_title',
# #         'citation_journal_title',
# #         'citation_author',
# #         'citation_publication_date',
# #         'citation_doi',
# #         'citation_isbn',
# #         'citation_issn',
# #         'citation_volume',
# #         'citation_issue',
# #         'citation_start_page',
# #         'citation_end_page',
# #         'citation_source1',
# #         'citation_source2',
# #         'citation_source3',
# #         'citation_source4',
# #         'external_system_id'
# #         ]
# #     end_range_column = 'S'
# #     header_end_range = 'S1'
# #     num_entries = len( all_results )
# #     data_end_range: str = f'{end_range_column}{num_entries + 1}'  # the plus-1 is for the header-row
# #     ## prepare data -------------------------------------------------
# #     data_values = []
# #     for entry in all_results:
# #         row = [
# #             entry['coursecode'],
# #             entry['section_id'],
# #             entry['citation_secondary_type'],
# #             entry['citation_title'],
# #             entry['citation_journal_title'],
# #             entry['citation_author'],
# #             entry['citation_publication_date'],
# #             entry['citation_doi'],
# #             entry['citation_isbn'],
# #             entry['citation_issn'],
# #             entry['citation_volume'],
# #             entry['citation_issue'],
# #             entry['citation_start_page'],
# #             entry['citation_end_page'],
# #             entry['citation_source1'],
# #             entry['citation_source2'],
# #             entry['citation_source3'],
# #             entry['citation_source4'],
# #             entry['external_system_id']
# #             ]
# #         data_values.append( row )
# #     log.debug( f'data_values, ``{data_values}``' )
# #     log.debug( f'data_end_range, ``{data_end_range}``' )
# #     new_data = [
# #         { 
# #             'range': f'A1:{header_end_range}',
# #             'values': [ headers ]
# #         },
# #         {
# #             'range': f'A2:{data_end_range}',
# #             'values': data_values
# #         }

# #     ]
# #     log.debug( f'new_data, ``{pprint.pformat(new_data)}``' )
# #     ## update values ------------------------------------------------
# #     # 1/0
# #     worksheet.batch_update( new_data, value_input_option='raw' )
# #     # worksheet.batch_update( new_data, value_input_option='USER_ENTERED' )
# #     ## update formatting --------------------------------------------
# #     worksheet.format( f'A1:{end_range_column}1', {'textFormat': {'bold': True}} )
# #     worksheet.freeze( rows=1, cols=None )
# #     ## re-order worksheets so most recent is 2nd --------------------
# #     wrkshts: list = sheet.worksheets()
# #     log.debug( f'wrkshts, ``{wrkshts}``' )
# #     reordered_wrkshts: list = [ wrkshts[0], wrkshts[-1] ]
# #     log.debug( f'reordered_wrkshts, ``{reordered_wrkshts}``' )
# #     sheet.reorder_worksheets( reordered_wrkshts )
# #     ## delete old checks (keeps current and previous) ---------------
# #     num_wrkshts: int = len( wrkshts )
# #     log.debug( f'num_wrkshts, ``{num_wrkshts}``' )
# #     if num_wrkshts > 3:  # keep requested_checks, and two recent checks
# #         wrkshts: list = sheet.worksheets()
# #         wrkshts_to_delete = wrkshts[3:]
# #         for wrksht in wrkshts_to_delete:
# #             sheet.del_worksheet( wrksht )
# #     return

# #     ## end def update_gsheet()
