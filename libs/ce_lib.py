from database_lib.book_lib_2 import Database, Book
from libs.dates import date_add_days, now, days_between_dates, validate_date
from libs.workflow import milestone_ready_to_process
from libs.maths import to_int

"""
There are complications in creating the data
The 'ready' date is not easily determined perhaps should be:-
    a: The actual completion date of previous process
    b: If above not available, then due date of previous process
       In any case the name might be changed to 'to_editing'
The forecast days in production - perhaps need to use the 'ready' date and due date
    - not the duration field
    Need to cope with extended duration, if late
Add queries field - extension requested - difficulty
Add PE - maybe hover?
Link to book edit page
"""

def get_books_in_copyedit():
    # Get the current books in copy edit and their status
    with Database() as DB:
        # Ignore previous milestone
        # Copy edit task must be unfinished
        list_of_books = DB.get_books(filter=is_inCopyedit) # With filter
        for bk in list_of_books:
            catno = bk['book']['catno']
            bk['copyedit'] = DB.get_copyedit_record(catno)
        print ('Number of books in copy edit:', len(list_of_books))
    return list_of_books

def is_inCopyedit(bk):
    return not bk['milestones']['copyedit']['end']

class CopyEdit():
    def __init__(self, book_obj): # book_obj from book_lib_2 with copyedit record added
        self.book_obj = book_obj
        self.book_rec = book_obj['book']
        self.mstone_rec = book_obj['milestones']
        self.ce_rec = book_obj['copyedit']
        self.catno = self.book_rec['catno']
        self.name = '{}'.format(self.book_rec['jobname'][:15])
        self.editor = self.ce_rec.get('editor','')
        self.pages = to_int(self.book_rec['mspages'])
        self.chapters = to_int(self.book_rec['nochapters'])
        self.complexity = self.book_rec['complexity']
        # Get ready, start, due and now
        process_dates(self) # Load dates for editing, ready, start, due
        """
        #self.days = to_int(self.mstone_rec['copyedit']['duration'])
        # Need to set up the various dates
        #  - ready
        #    start
        #    now
        #    due
        #    late
        #try:
        #    self.ready = date_add_days(self.due, -int(self.days))
        #except:
        #    self.ready = '' # The planned start date
        self.start = self.mstone_rec['copyedit']['start']
        if not validate_date(self.start):
            self.start = ''
        self.due = self.mstone_rec['copyedit']['due']
        if not validate_date(self.due):
            self.due = ''
        self.ready =  milestone_ready_to_process(self.mstone_rec, 'copyedit')
        """
        if self.ready and self.due:
            self.days = days_between_dates(self.ready, self.due)
        else:
            self.days = 0
        if self.ready:
            self.days_gone = days_gone(self.ready)
        else:
            self.days_gone = 0
        self.remaining_days = max(0, self.days - self.days_gone)
        try:
            self.initial_speed = int(self.pages * 5 / self.days)
        except:
            self.initial_speed = 0
        self.done_pages = to_int(self.ce_rec.get('done_pages', 0))
        self.done_chapters = to_int(self.ce_rec.get('done_chapters', 0))
        self.remaining_pages = self.pages - self.done_pages
        self.remaining_chapters = self.chapters - self.done_chapters
        try:
            self.remaining_speed = int(self.remaining_pages * 5 / self.remaining_days)
        except:
            self.remaining_speed = 0
        # Get timeline percentages and length
        self.queries = self.ce_rec.get('queries','')
        self.timeline = timeline_data(self)

def process_dates(bk):
    # Create ready, start and due dates
    bk.start = bk.mstone_rec['copyedit']['start']
    if not validate_date(bk.start):
        bk.start = ''
    bk.due = bk.mstone_rec['copyedit']['due']
    if not validate_date(bk.due): # Cannot show chart
        bk.due = ''
    bk.ready =  milestone_ready_to_process(bk.mstone_rec, 'copyedit') # Date validated
    if not bk.ready and bk.start:
        bk.ready = bk.start
    if bk.start and  bk.ready > bk.start:
        bk.ready = bk.start
    if bk.ready > bk.due:  # This needs some more thought
        bk.ready = ''

def timeline_data(obj):
    # Need length, -> missed, used, available, late - percents of length
    length = 0
    obj.box_len = 0
    obj.missed_x = 0
    obj.missed_len = 0
    obj.used_x = 0
    obj.used_len = 0
    obj.available_x = 0
    obj.available_len = 0
    obj.late_x = 0
    obj.late_len = 0
    today = now()[:10]
    if obj.ready and obj.due:
        if obj.start > today: obj.start = '' # Impossible
        if obj.due > today:
            length = days_between_dates(obj.ready, obj.due)
            if obj.start:
                missed = days_between_dates(obj.ready, obj.start)
                used = days_between_dates(obj.start, today)
                available = days_between_dates(today, obj.due)
                late = 0
            else:
                missed = days_between_dates(obj.ready, today)
                used = 0
                available = days_between_dates(today, obj.due)
                late = 0
        else:
            length = days_between_dates(obj.ready, today)
            if obj.start:
                if obj.start < obj.due:
                    missed = days_between_dates(obj.ready, obj.start)
                    used = days_between_dates(obj.start, obj.due)
                    available = 0
                    late = days_between_dates(obj.due, today)
                else:
                    missed = days_between_dates(obj.ready, obj.due)
                    used = 0
                    available = 0
                    late = days_between_dates(obj.due, today)
            else:
                missed = days_between_dates(obj.ready, obj.due)
                used = 0
                available = 0
                late = days_between_dates(obj.due, today)
        try:
            obj.missed_perc = int(missed * 100 / length)
            obj.used_perc = int(used * 100 / length)
            obj.available_perc = int(available * 100 / length)
            obj.late_perc = int(late * 100 / length)
            # scg coordinates
            obj.missed_x = 0
            obj.missed_len = missed * 5
            obj.used_x = obj.missed_x + obj.missed_len + 1
            obj.used_len = used * 5
            obj.available_x = obj.used_x + obj.used_len + 1
            obj.available_len = available * 5
            obj.late_x = obj.available_x + obj.available_len + 1
            obj.late_len = late * 5
            obj.box_len = obj.late_x + obj.late_len
        except:
            obj.missed_perc = 0
            obj.used_perc = 0
            obj.available_perc = 100
            obj.late_perc = 0
    else: # No length
        obj.missed_perc = 0
        obj.used_perc = 0
        obj.available_perc = 100
        obj.late_perc = 0
    obj.length = length
    #if length:
        #print (obj.ready, obj.start, obj.due, today, ":", length, missed, used, available, late, ":",
        #       obj.missed_perc, obj.used_perc, obj.available_perc, obj.late_perc)


def days_gone(date):
    if validate_date(date):
        today = now()
        #print(date, today)
        return days_between_dates(date, today)
    return 0