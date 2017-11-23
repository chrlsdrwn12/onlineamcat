"""
  Convert fields from the olf (Production->Jobs) collection
  to the new tables
     CRC->Books
     CRC->Milestones
"""

# Books field conversion

To_Books = {}
To_Books['name'] = 'catno'
To_Books['jobname'] = 'jobname'
To_Books['received'] = 'received'
To_Books['estpages'] = 'typesetpages'
To_Books['mspages'] = 'mspages'
To_Books['no_chapters'] = 'nochapters'
To_Books['no_tables'] = 'notables'
To_Books['no_figures'] = 'nofigures'
To_Books['no_equations'] = 'noequations'
To_Books['isbn'] = 'isbn'
To_Books['booktype'] = 'booktype'
To_Books['appendices'] = 'appendices'
To_Books['PE'] = 'PE'
To_Books['title'] = 'title'
#To_Books['complexity'] = 'complexity' - not currently in jobs
#To_Books['category'] = 'category'
To_Books['author'] = 'author'

From_Books = {}
for key in To_Books:
    From_Books[To_Books[key]] = key

To_Milestone = {}
To_Milestone['ced'] = 'copyedit'
To_Milestone['initial'] = 'typeset1'
To_Milestone['2ndpages'] = 'secondpages'
To_Milestone['proofread'] = 'proofread'
To_Milestone['finalpages'] = 'voucherproofs'
To_Milestone['printer'] = 'printerPDF'

From_Milestones = {}
for key in To_Milestone:
    From_Milestones[To_Milestone[key]] = key

def milestone_to_jobs_keys(milestone_key):
    # e.g. copyedit|due
    # returns duedates, ced
    action = {'end': 'deliverydates', 'due':'duedates', 'start': '', 'duration':''}
    base, field = milestone_key.split('|')
    action_key = action.get(field, '')
    stage_key = From_Milestones.get(base, '')
    return action_key, stage_key

def jobs_to_milestone_key(jobs_key):
    # e.g. deliverydates|ced
    # returns copyedit|end
    action = {'deliverydates':'end', 'duedates':'due', 'start': ''}
    base, field = jobs_key.split('|')
    when = action.get(base, '')
    ans = ''
    if when:
        stage = To_Milestone.get(field, '')
        if stage:
            ans = '{}|{}'.format(stage, when)
    return ans

# Add all the milestones here, not just the duedates and delivery dates
# Assume the fields are provided with | e.g. copyedit:start
job_fields = ['name','jobname','received','estpages','mspages','no_chapters', 'no_tables',
               'no_figures','no_equations','isbn','booktype','appendices','PE', 'author', 'title',
               'comment:ced','comment:initial', 'comment:2ndpages', 'comment:finalpages']

book_fields = ['catno', 'jobname','received','typesetpages','mspages', 'nochapters', 'notables',
               'nofigures','noequations','isbn','booktype','appendices','PE', 'author', 'proofreader',
               'complexity','category', 'maineditor', 'title', 'ebook', 'deleted', 'latequeries',
                'extension', 'projectmanager']

# There is also a field comment - with child fields for the milestone (e.g. comment:proofread) - no field if no entry
# So no blanks are created for all the milestone comment fields - only created when needed

# These are for printer pdf production, the edeliverable fields are not useful
all_milestones = ['editqueries', 'copyedit', 'typeset1', 'secondpages','proofread','voucherproofs', 'printerPDF',
                  'castoff','artwork','aureview', 'combine','index', 'template', 'typeset2', 'typeset3',
                  'XMLin','XMLout','eBook','webPDF','CRCdeliverable','HSSdeliverable', 
                  'logistics', 'corrections', 'finalpages', 'LOC']

milestone_fields = ['due','start','end', 'duration']


copyedit_fields = [ 'editor', 'pre_edittool', 'post_edittool','done_pages',
                    'done_chapters','speed','finished', 'queries', 'ce_comment'] 

eDeliverable_fields = ['eRefXML', 'eWebPDF', 'eBodyXML', 'eBookXML', 'ePub', 'eDelivered', 'eEstimate', 'eDue']

"""


                #'target_w1_pages', 'target_w1_chapters',
                    #'target_w2_pages', 'target_w2_chapters',
                    'target_w3_pages', 'target_w3_chapters',
                    'target_w4_pages', 'target_w4_chapters',
                    'target_w5_pages', 'target_w5_chapters',
                    'actual_w1_pages', 'actual_w1_chapters',
                    'actual_w2_pages', 'actual_w2_chapters',
                    'actual_w3_pages', 'actual_w3_chapters',
                    'actual_w4_pages', 'actual_w4_chapters',
                    'actual_w5_pages', 'actual_w5_chapters'
                    ]
"""
# Create a list of date fields, these will be validated before being saved to database using Book class
date_fields = []
for mstone in all_milestones:
    date_fields.append('{}|{}'.format(mstone, 'start'))
    date_fields.append('{}|{}'.format(mstone, 'due'))
    date_fields.append('{}|{}'.format(mstone, 'end'))
date_fields.append('finished')

def field_data_conversion(book_obj, field, value):
    # If field is date and value is short, adjust to long date format
    # Used before stroing in database
    print ('-'*70)
    print ('Checking format of data. Orignial field - format', field, value)
    print (field, value)
    if len(value) == 5: # Possible short date
        if field in date_fields: # Need to expand to yyy-mm-dd
            # Need to get received date for base date
            recvd = book_obj.get_field('received')
            #print (recvd)
            if recvd:
                value = value.replace('/', '-')
                year = int(recvd[:4])
                month = int(recvd[5:7])
                #print (year, month)
                data_month = int(value[:2])
                #print (data_month)
                if data_month < month: # Same year
                    year += 1
                value = '{}-{}'.format(year, value)
    #print ('Adjusted value', value)
    return value


def update_from_Jobs(client, job_record, deleteall = False):
    # Update the CRC database, collections Books and Milestones
    # From the Jobs record
    job_record.pop('_id', '')
    db = client.CRC
    if deleteall:
        db.Books.delete_many({})
        db.Milestones.delete_many({})
    # --------------------------------------------------------------------------
    # Books
    # --------------------------------------------------------------------------
    collection = db.Books
    book_rec = {}
    for key in job_record:
        if key in To_Books:
            book_rec[To_Books[key]] = job_record[key]
        elif key in book_fields:
            book_rec[key] = job_record[key]
    collection.update( {'jobname': job_record['jobname']},{"$set": book_rec}, upsert=True)
    print (job_record['name'])
    print (book_rec)
    # --------------------------------------------------------------------------
    # Milestones
    # --------------------------------------------------------------------------
    collection = db.Milestones
    milestone_record = collection.find_one({'jobname': job_record['jobname']})
    if not milestone_record:
        milestone_record = {'catno': job_record[From_Books['catno']], 'jobname': job_record[From_Books['jobname']]}
    print ('Milestone job', milestone_record)
    duedates = job_record.get('duedates', {})
    deliverdates = job_record.get('deliverdates', {})
    for key in duedates:
        milestone = To_Milestone[key]
        print (key, milestone)
        if milestone not in milestone_record:
            milestone_record[milestone] = {'due': '', 'start': '', 'end':''}
        milestone_record[milestone]['due'] = duedates[key]
    print ('-'*70)
    for key in duedates:
        print ('{:14} : {} : {}'.format(key, duedates[key], deliverdates.get(key,'N/A')))
    for key in duedates:
        milestone = To_Milestone[key]
        print ('{:14} : {} : {}'.format(milestone, milestone_record[milestone]['due'], milestone_record[milestone]['end'] ))
    print ('-'*70)
    for key in deliverdates:
        milestone = To_Milestone[key]
        print (key, milestone)
        if milestone not in milestone_record:
            milestone_record[milestone] = {'due': '', 'start': '', 'end':''}
        milestone_record[milestone]['end'] = deliverdates[key]

    print ('Milestone job', milestone_record)
    for key in duedates:
        print ('{:14} : {} : {}'.format(key, duedates[key], deliverdates.get(key,'N/A')))
    print ('-'*70)
    for key in duedates:
        milestone = To_Milestone[key]
        print ('{:14} : {} : {}'.format(milestone, milestone_record[milestone]['due'], milestone_record[milestone]['end'] ))
    collection.update( {'jobname': milestone_record['jobname']},{"$set": milestone_record}, upsert=True)
