from pymongo import MongoClient
from database_lib.config import ip, port
from database_lib.conversion import book_fields, all_milestones, copyedit_fields, date_fields
from database_lib.conversion import From_Books, From_Milestones, milestone_to_jobs_keys, field_data_conversion
from database_lib.conversion import eDeliverable_fields
from libs.dates import validate_date
"""
------------------------------------------------------------------------------------------
   Database()

     Loads the Jobs, Books and Milestones collections and creates dictionary of catno
     self.client
     self.jobs
     self.books
     self.milestones
     self.job_dct
     self.book_dct
     self.milestones_dct

     get_books(filter)
     get_copyedit_record(catno)

------------------------------------------------------------------------------------------
   Book(catno)
     -- Note we treat comment:stage in a separate way - use comments dictionary

     update_field(field, value) - determines which collection the field is in - save to collection(s)
     get_field(field)
------------------------------------------------------------------------------------------

   update_fields(changes) - updates the book fields with data, field can be combined field (e.g. copyedit|due)
     changes is list of key, value dict
     key is catno-field

   get_fields(book, fields) # Extract list of fields from book, returns list fo field data
------------------------------------------------------------------------------------------
def remove_reprints()
   Removes books from the books collection whose jobname ends with _reprint
   To use manually type /removereprints in url
------------------------------------------------------------------------------------------

   Filters used in Database.get_books:-
     all_books_filter
     live_book_filter


   These functions used when displaying data in reports - should not be in this file:-
   no_formatting(value) # return value unchanged
   short_date(value) # Convert yyyy-mm-dd to mm/dd

------------------------------------------------------------------------------------------
"""

# ----------------------------------------------------------------------------------------------------------------------
# Book Filters
# ----------------------------------------------------------------------------------------------------------------------
def all_books_filter(book): # All books!!
    return True

def live_book_filter(book):
    return book['milestones']['printerPDF']['end'] == ''

def voucherProofFilter(book):
    return book['milestones']['voucherproofs']['end'] != ''
    

class Database():
    #with Database() as DB:
    # use DB
    def __init__(self):
        self.client = MongoClient(ip, port)
        self.jobs = list(self.client.Production.Jobs.find({}, {'_id': False}))
        self.books = list(self.client.CRC.Books.find({}, {'_id': False}))
        self.milestones = list(self.client.CRC.Milestones.find({}, {'_id': False}))
        self.job_dct = {job['name']:job for job in self.jobs}
        self.book_dct = {book['catno']:book for book in self.books}
        self.milestone_dct = {m_stone['catno']:m_stone for m_stone in self.milestones}

    def get_books(self, filter=all_books_filter):
        """
        Create a list of book objects (obj or dict)
        :param filter - books to include:
        :return: List of book objects/dicts
        """
        books = []
        for book in self.books:
            bk = {'book':book}
            catno = book['catno']
            bk['milestones'] = self.milestone_dct.get(catno, {})
            if filter(bk):
                books.append(bk)
        return books

    def get_copyedit_record(self, catno):
        collection = self.client.CRC.CopyEdit
        copyedit_record = collection.find_one({'catno':catno}, {'_id': False})
        if not copyedit_record:
            copyedit_record = {}
        return copyedit_record

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

class Book():
    def __init__(self, catno):
        self.client = MongoClient(ip, port)
        self.catno = catno

    def save_book_changes(self, changes):
        # change is 'K12345-field'
        for key in changes:
            catno, field = key.split('-')
            value = changes[key]
            self.update_field(field, value)

    def update_field(self, field, value):
        # Valid fields are fields from Books, Milestones and CopyEdit collections
        # Check if field exists in books, milestones or copyedit collections
        # Also update Jobs if there is a corresponding Jobs record
        status = True
        value = field_data_conversion(self, field, value)
        #print (field, value)
        if field in date_fields:
            #print ('Date field', field)
            # Allow blank fields
            if value:
                if not validate_date(value):
                    #print ('Failed - wrong data')
                    return False # Data invalid
        if field in book_fields:
            self.update_book_collection(field, value)
            job_field = From_Books.get(field, '')
            if job_field:
                status = self.update_jobs(field, value)
        elif field in copyedit_fields:
            #print ('Copy edit field')
            status = self.update_copyedit(field, value)
        elif field in eDeliverable_fields:
            status = self.update_eDeliverable(field, value)
        else: # Should be milestone
            if '|' in field: # Milestone
                milestone, key_field = field.split('|')
                if milestone in all_milestones:
                    status = self.update_milestone(milestone, key_field, value)
                    delivery_due_field, stage = milestone_to_jobs_keys(field) # stage = initial, ced etc.
                    if delivery_due_field and stage:
                        status = self.update_job(delivery_due_field, value, stage) # e.g deliverdates, value, ced
                else:
                    status = False
            elif ':' in field: # Comment
                status = False # Default to error
                fields = field.split(':')
                if len(fields) == 2:
                    if fields[0] == 'comment':
                        # Stage comment field
                        status = self.update_comment(fields[1], value)
            else:
                status = False
        return status

    def update_milestone(self, mstone, field, value):
        # mstone is milestone e.g. copyedit , field is key i.e. srat, due, end, duration
        print ('Update milestones record')
        print (mstone, field, value)
        if mstone in all_milestones:
            db = self.client.CRC
            collection = db.Milestones
            record = collection.find_one({'catno':self.catno},  {'_id': False})
            if record: # The mstone field should exist
                record[mstone][field] = value
                collection.update( {'catno': self.catno},{"$set": record})
                return True
            else:
                self.display_error('Milestone record for {} not foound'.format(self.catno))
        else:
            self.display_error('Field {} not in milestones field list'.format(mstone))
        return False

    def update_book_collection(self, field, value):
        if field in book_fields:
            db = self.client.CRC
            books_collection = db.Books
            book_record = books_collection.find_one({'catno':self.catno}, {'_id': False})
            if book_record:
                book_record[field] = value
                books_collection.update( {'catno': self.catno},{"$set": book_record})
                return True
            else:
                self.display_error('Book record for {} not foound'.format(self.catno))
        else:
            self.display_error('Field {} not in book field list'.format(field))
        return False

    def update_comment(self, comment_key, value):
        print ('Adding comment:', comment_key, value)
        db = self.client.CRC
        books_collection = db.Books
        book_record = books_collection.find_one({'catno':self.catno}, {'_id': False})
        if book_record:
            if 'comment' not in book_record:
                book_record['comment'] = {}
            book_record['comment'][comment_key] = value
            books_collection.update( {'catno': self.catno},{"$set": book_record})
            return True
        else:
            return False


    def update_job(self, field, value, key=''):
        """
           For simple field (e.g. received, field='received', value = date
           For complex, field is first dict (e.g. duedates) second is stage (e.g. ced, initial)
        """
        #print ('Update Jobs record - not implemented')
        #print (field, value, key)
        db = self.client.Production
        collection = db.Jobs
        job_record = collection.find_one({'name':self.catno}, {'_id': False})
        if job_record:
            if key: # e.g delivery or due dates
                job_record[field][key] = value

            else:  # simple field
                job_record[field] = value
            collection.update({'name': self.catno},{"$set": job_record})
            #self.display_error('Update Jobs not implemented')
        else:
            self.display_error('Book record for {} not foound'.format(self.catno))
        return False

    def update_copyedit(self, field, value):
        db = self.client.CRC
        copyedit_collection = db.CopyEdit
        #print (list(self.client.CRC.CopyEdit.find({}, {'_id': False})))
        copyedit_record = copyedit_collection.find_one({'catno':self.catno},  {'_id': False})
        if not copyedit_record:
            copyedit_record = {}
            copyedit_record['catno'] = self.catno
            copyedit_collection.insert( copyedit_record)
        copyedit_record[field] = value
        #print (copyedit_record)
        copyedit_collection.update( {'catno': self.catno},{"$set": copyedit_record})
        return True

    def update_eDeliverable(self, field, value):
        db = self.client.CRC
        eDeliverable_collection = db.eDeliverable
        #print (list(self.client.CRC.CopyEdit.find({}, {'_id': False})))
        eDeliverable_record = eDeliverable_collection.find_one({'catno':self.catno},  {'_id': False})
        if not eDeliverable_record:
            eDeliverable_record = {}
            eDeliverable_record['catno'] = self.catno
            eDeliverable_collection.insert( eDeliverable_record)
        eDeliverable_record[field] = value
        #print (copyedit_record)
        eDeliverable_collection.update( {'catno': self.catno},{"$set": eDeliverable_record})
        return True

    def get_field(self, field):
        # Determine which collection, then get field value
        value = ''
        if field in book_fields:
            db = self.client.CRC
            books_collection = db.Books
            book_record = books_collection.find_one({'catno':self.catno}, {'_id': False})
            if book_record:
                if field in book_record:
                    value = book_record[field]
                else:
                    self.display_error('Field not found in book record {}'.format(field))
            else:
                self.display_error('Catno not found in books collection {}'.format(self.catno))
        elif field in copyedit_fields:
            db = self.client.CRC
            copyedit_collection = db.CopyEdit
            copyedit_record = copyedit_collection.find_one({'catno':self.catno},  {'_id': False})
            if copyedit_record:
                if field in copyedit_record:
                    value = copyedit_record[field]
                else:
                    self.display_error('Field not found in copyedit record {}'.format(field))
            else:
                self.display_error('Catno not found in copyedit collection {}'.format(self.catno))
        elif '|' in field: # Milestone
            db = self.client.CRC
            collection = db.Milestones
            record = collection.find_one({'catno':self.catno},  {'_id': False})
            if record: # The milestone field should exist
                milestone, key_field = field.split('|')
                if milestone in record:
                    record[milestone][field] = value
                else:
                    self.display_error('Field not found in milestones record {}'.format(milestone))
            else:
                self.display_error('Catno not found in milestones collection {}'.format(self.catno))
        elif ':' in field: # Comment for milestone (comment:stage)
            fieldname, stage = field.split(':')
            if fieldname == 'comment':
                db = self.client.CRC
                books_collection = db.Books
                book_record = books_collection.find_one({'catno':self.catno}, {'_id': False})
                if 'comment' not in book_record:
                    book_record['comment'] = {}
                    value = book_record['comment'].get(stage, '')
            else:
                self.display_error('Get field for {} not implemented'.format(field))
        else:
            self.display_error('Get field for {} not implemented'.format(field))
        return value

    def display_error(self, error):
        print ('-'*70)
        print (error)
        print ('-'*70)

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

def update_fields(changes):
    # changes is list of key, value dict
    # key is catno-field
    ans = 'OK'
    for key in changes:
        catno, field = key.split('-')
        value = changes[key]
        print (catno, field, value)
        with Book(catno) as book:
            if not book.update_field(field, value):
                ans = 'Fail'
    return ans

# ----------------------------------------------------------------------------------------------------------------------
# Lists of books
# ----------------------------------------------------------------------------------------------------------------------

def get_fields(book, fields):
    # Get row of field values from a book dct
    # Use only books and milestones collections
    bk = []
    unused_fields = []
    for field in fields:
        if '|' in field: # Milestone
            milestone, key_field = field.split('|')
            if milestone in all_milestones:
                value = book['milestones'].get(milestone, {}).get(key_field, '')
                bk.append(value)
            else:
                unused_fields.append(field)
        else: # Header field
            if field in book_fields:
                value = book['book'].get(field, '')
                bk.append(value)
            else:
                unused_fields.append(field)
    if unused_fields:
        print ('-'*70)
        print ('WARNING: These fields not found')
        for fld in unused_fields:
            print ('..', fld)
        print ('-'*70)
    return bk

# ----------------------------------------------------------------------------------------------------------------------
# Formating functions
# ----------------------------------------------------------------------------------------------------------------------
def remove_reprints():
    print ('Removing reporints')
    with Database() as DB:
        for book in DB.books:
            #print (book['jobname'])
            if book['jobname'].lower().endswith('_reprint'):
                DB.client.CRC.Books.delete_one({'catno': book['catno']})
# ----------------------------------------------------------------------------------------------------------------------
# Formating functions
# ----------------------------------------------------------------------------------------------------------------------
def no_formatting(value):
    return value

def short_date(value):
    return value[-5:].replace('-','/')