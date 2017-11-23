#
from pymongo import MongoClient
from database_lib.conversion import book_fields, all_milestones, milestone_to_jobs_keys
from database_lib.conversion import From_Milestones, From_Books, update_from_Jobs, job_fields
from database_lib.config import ip, port

class Database():
    #with Database() as DB:
    # use DB
    def __init__(self, load=True):
        self.client = MongoClient(ip, port)
        if load:
            self.jobs = list(self.client.Production.Jobs.find({}, {'_id': False}))
            self.books = list(self.client.CRC.Books.find({}, {'_id': False}))
            self.milestones = list(self.client.CRC.Milestones.find({}, {'_id': False}))
            self.job_dct = {job['name']:job for job in self.jobs}
            self.book_dct = {book['catno']:book for book in self.books}
            self.milestone_dct = {m_stone['catno']:m_stone for m_stone in self.milestones}

    def saveJob(self, catno):
        job = self.job_dct.get(catno,'')
        if job:
            self.client.Production.Jobs.update( {'name': catno},{"$set": job})
            return True
        return False

    def saveBook(self, catno):
        book = self.book_dct.get(catno,'')
        if book:
            self.client.CRC.Books.update( {'catno': catno},{"$set": book})
            return True
        return False

    def saveMilestones(self, catno):
        m_stone = self.milestone_dct.get(catno,'')
        if m_stone:
            self.client.CRC.Milestones.update( {'catno': catno},{"$set": m_stone})
            return True
        return False

    def insert_book(self, book):
        if book['catno'] in self.book_dct:
            return False
        if not book['catno']:
            return False
        self.client.CRC.Books.insert(book)
        self.book_dct[book['catno']] = book
        self.books.append(book)
        return True

    def insert_milestone(self, milestone):
        if milestone['catno'] in self.milestone_dct:
            return False
        if not milestone['catno']:
            return False
        self.client.CRC.Milestones.insert(milestone)
        self.milestone_dct[milestone['catno']] = milestone
        self.milestones.append(milestone)
        return True

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

def get_connection(ip, port):
    return MongoClient(ip, port)
    if server:
        mongo = MongoClient('192.168.0.100', 27017 )
    else: # Local mongo server
        mongo = MongoClient('localhost', 27017 )
        
def close_connection(client):
    client.close()

def loadBook(query, fields = None):
    # Which fields to get?
    # Which database
    # How to format the combined fields (milestones) with |
    # Which field takes priority Jobs or Books, or Milestones
    # query {'catno': catno}
    # Get catno
    catno = query.get('catno','') 
    book = Book()
    if not catno:
        catno = book.get_catno(query)
        if not catno:
            print ('xxx') # Fail
    bk = {}
    if book.get_records(catno):
        unused_fields = []
        if not fields:
            fields = book_fields # All book fields
        for field in fields:
            if '|' in field: # Milestone
                milestone, key_field = field.split('|')
                if milestone in all_milestones:
                    job_stage = From_Milestones.get(milestone, '') # ced, initial etc.
                    job_field = {'end': 'deliverydates', 'due':'duedates', 'start': ''}.get(key_field, '')
                    if job_stage and job_field: # Data in Jobs
                        value = book.job_record.get(job_field, {}).get(job_stage, '')
                        bk[field] = value
                        #print (field, milestone, key_field, job_field, job_stage, value)
                    else: # Data in Miletsones
                        value = book.milestones_record.get(milestone, {}).get(key_field, '')
                        #print (field, milestone, key_field, '=', value)
                        bk[field] = value
                else:
                    unused_fields.append(field)
            else: # Header field
                if field in book_fields:
                    job_field = From_Books.get(field, '')
                    if job_field:
                        value = book.job_record.get(job_field, '')
                    else:
                        value = book.books_record.get(field, '')
                    bk[field] = value
                else:
                    unused_fields.append(field)
        #print (bk)
        if unused_fields:
            print ('-'*70)
            print ('WARNING: These fields not found')
            for fld in unused_fields:
                print ('..', fld)
            print ('-'*70)
    else:
        print ('Unable to load book data', catno)
    return bk

def updateBook(record):
    # Save to Books, Milestones and Jobs
    # List extraneous fields (not found in collections) - do not add
    unused_fields = []
    catno = record.get('catno','') 
    if not catno:
        if 'prodname' in record:
            catno = book.get_catno({'prodname': record['prodname']})
            if not catno:
                print ('xxx') # Fail
    print ('Updating', catno)
    # partial updating does not seem to work for {duedates][printer]}
    # So read entire job record
    # Also consider not using [milestones][due] but milestones|due
    book = Book()
    book.get_records(catno)
    # Flags to see if records needs saving
    job_changed = False
    book_changed = False
    milestone_changed = False
    if book.job_record: # Use book.get_records() instead
        for field, value in record.items():
            if '|' in field: # Milestone
                milestone, key_field = field.split('|')
                if milestone in all_milestones:
                    job_stage = From_Milestones.get(milestone, '') # ced, initial etc.
                    #print (field, milestone, job_stage, value)
                    job_field = {'end': 'deliverydates', 'due':'duedates', 'start': ''}.get(key_field, '')
                    if job_stage and job_field: # Data in Jobs
                        if job_field not in book.job_record:
                            book.job_record[job_field] = {}
                        book.job_record[job_field][job_stage] = value
                        job_changed = True
                    #print (milestone, key_field, value, job_stage, job_field)
                    #print (book.job_record)
                    if milestone not in book.milestones_record:
                        book.milestones_record[milestone] = {}
                    book.milestones_record[milestone][key_field] = value
                    milestone_changed = True
                else:
                    unused_fields.append(field)
            else:
                if field in book_fields:
                    job_field = From_Books.get(field, '')
                    if job_field:
                        book.job_record[job_field] = value
                        job_changed = True
                    print (field, value)
                    book.books_record[field] = value
                    book_changed = True
                elif field in job_fields:
                    book.job_record[field] = value
                    job_changed = True

                else:
                    unused_fields.append(field)
    else:
        print ('Unable to load book data', catno)
    if unused_fields:
        print ('-'*70)
        print ('WARNING: These fields not found in database')
        for fld in unused_fields:
            print ('..', fld)
        print ('-'*70)
    #print (job_rec)
    #print (book_rec)
    #print (milestone_rec)
    client = MongoClient(ip, port) #'localhost', 27017)
    if job_changed:
        db = client.Production
        collection = db.Jobs
        print ('Saving job record', catno)
        collection.update( {'name': catno},{"$set": book.job_record})
        #print (job_rec)
    if book_changed:
        print ('Book changed')
        db = client.CRC
        collection = db.Books
        collection.update( {'catno': catno},{"$set": book.books_record})
    if milestone_changed:
        db = client.CRC
        collection = db.Milestones
        collection.update( {'catno': catno},{"$set": book.milestones_record})
    client.close()

def get_all_job_records():
    client = MongoClient(ip, port)
    jobs =  client.Production.Jobs.find({}, {'_id': False})
    client.close()
    return jobs

def save_job_record(job):
    client = MongoClient(ip, port)
    client.Production.Jobs.update( {'name': job['name']},{"$set": job})
    client.close()


def get_catnos():
    # Get all the book catnos - from Books, not Jobs later add filter
    #client = MongoClient('localhost', 27017)
    client = MongoClient(ip, port)
    db = client.CRC
    collection = db.Books
    all_books = collection.find({})
    return [x['catno'] for x in all_books]

def addBook(job):
    # Add to Jobs, then add to Books and Milestones
    client = MongoClient(ip, port) # 'localhost', 27017)
    db = client.Production
    jobs_collection = db.Jobs
    jobs_collection.update( {'name': job['name']},{"$set": job}, upsert=True)
    update_from_Jobs(client, job)

def get_job_record(catno):
    # If job record exists in Jobs
    client = MongoClient(ip, port) #'localhost', 27017)
    db = client.Production
    jobs_collection = db.Jobs
    job_record = jobs_collection.find_one({'name':catno})
    client.close()
    return job_record

def get_all_books(fields, reprints=False):
    # Get all books returning list of book objects from Books collection
    with Database() as DB:
        data = []
        book_obj = Book() # Avoid using the in-built get record to stop repeated connecting to mongodb
        for book in DB.books: # Ignore those older books and reprints
            if book.get('deleted', 'N') != 'Y':
                bk = {}
                catno = book['catno']
                book_obj.job_record = DB.job_dct[catno]
                book_obj.books_record = book #DB.book_dct.get(catno, {}) # db.Books.find_one({'catno':catno})
                book_obj.milestones_record = DB.milestone_dct.get(catno, {}) # db.Milestones.find_one({'catno':catno})
                data.append(get_fields(book_obj, fields))
    return data

def get_fields(book, fields): # Get row of field values from a book class
                              # Gets records from Jobs, Books and Milestones
    bk = []
    unused_fields = []
    for field in fields:
        if '|' in field: # Milestone
            milestone, key_field = field.split('|')
            if milestone in all_milestones:
                job_stage = From_Milestones.get(milestone, '') # ced, initial etc.
                job_field = {'end': 'deliverydates', 'due':'duedates', 'start': ''}.get(key_field, '')
                if job_stage and job_field: # Data in Jobs
                    # Temporary try to avoid bad data
                    try:
                        value = book.job_record.get(job_field, {}).get(job_stage, '')
                    except:
                        value = ''
                    bk.append(value)
                    #print (field, milestone, key_field, job_field, job_stage, value)
                else: # Data in Miletsones
                    value = book.milestones_record.get(milestone, {}).get(key_field, '')
                    #print (field, milestone, key_field, '=', value)
                    bk.append(value)
            else:
                unused_fields.append(field)
        else: # Header field
            if field in book_fields:
                job_field = From_Books.get(field, '')
                if job_field:
                    value = book.job_record.get(job_field, '')
                else:
                    value = book.books_record.get(field, '')
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

class Book():
    def __init__(self):
        self.catno = ''
        self.job_record = {}
        self.books_record = {}
        self.milestones_record = {}

    def get_records(self, catno, client=None):
        # Load all the records from Jobs, Books and Milestones
        self.catno = catno
        opened = False
        if not client:
            client = MongoClient(ip, port) #'localhost', 27017)
            opened = True
        db = client.Production
        jobs_collection = db.Jobs
        self.job_record = jobs_collection.find_one({'name':catno})
        if not self.job_record:
            print ("Catno not in Jobs")
            return False
        # Fix date underscore!
        if 'received' in self.job_record:
            self.job_record['received'] = self.job_record['received'].replace('_','-')
        db = client.CRC
        books_collection = db.Books
        self.books_record = books_collection.find_one({'catno':catno})
        if not self.books_record:
            self.books_record = {}
        milestones_collection = db.Milestones
        self.milestones_record = milestones_collection.find_one({'catno':catno})
        if not self.milestones_record:
            self.milestones_record = {}
        if opened:
            client.close()
        return True

    def get_catno(self, query):
        client = MongoClient(ip, 27017)
        db = client.CRC
        books_collection = db.Books
        record = books_collection.find_one(query)
        if record:
            return record['catno']
        return ''

    def get_field(self, fieldname):
        return get_fields(self, [fieldname])[0]