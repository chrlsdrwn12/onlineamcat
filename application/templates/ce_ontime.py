from libs.ce_lib import get_books_in_copyedit, CopyEdit, Book

ontime_headers = ['Book','Pages', 'CE','Due', 'Comment/Status', 'Update']

def CE_ontime_status():
    print ('CE Online')
    data = []
    books = get_books_in_copyedit()
    for bk in books:
        catno = bk['book']['catno']
        #print (catno)
        #book_data = CopyEdit(bk)
        #row = create_html_row(book_data)
        #data.append(row)
        row = {}
        row['book'] = catno
        row['pages'] = bk['book']['mspages']
        row['CE'] = bk['copyedit'].get('editor','')
        row['due'] = bk['milestones']['copyedit']['due']
        row['comment'] = bk['copyedit'].get('ce_comment','')
        data.append(row)
    return data

def save_ontime(record):
    catno = record['updatebook']
    print (record)
    with Book(catno) as bk:
        bk.update_field('ce_comment', record['comment'])
