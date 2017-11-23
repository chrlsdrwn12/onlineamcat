from libs.dates import validate_date


previous = {'copyedit': ['logistics'],
            'proofread': ['typeset1']}

next = {'copyedit':['XMLin']}

def previous_milestones(mstone):
    return previous.get(mstone,[])


def previous_completed(book, previous_milestones):
    #print (previous_milestones)
    #print (book['milestones']['logistics']['end'])
    if book['milestones']['logistics']['end']:
        return True
    return False

def complete(book, mstone):
    if book['milestones'][mstone]['end']:
        return True
    return False

def milestone_ready_to_process(mstones_dct, mstone):
    """
    Get the date the milestone was ready or is due to be ready
    If previous milestone is completed, then we have the actual ready date of this milestone
    If not then we use the due date of the previous milestone
    """
    ans = ''
    previous_mstones = previous_milestones(mstone)
    if previous_mstones:
        previous_mstone = previous_mstones[0]
        if mstones_dct[previous_mstone]['end']:
            ans = mstones_dct[previous_mstone]['end']
        else:
            ans = mstones_dct[previous_mstone]['due']
    if not validate_date(ans):
        ans = ''
    return ans