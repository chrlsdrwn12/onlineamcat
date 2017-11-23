from flask import render_template, session, request, jsonify, redirect, flash, url_for
from functools import wraps

from application.templates.ce_ontime import CE_ontime_status, ontime_headers, save_ontime


from flask import Blueprint

CEmod = Blueprint('CE', __name__, url_prefix='/CE', template_folder='templates', static_folder='static')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('You need to login first.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@login_required    
def test():
    return render_template('test.html', **locals())

@CEmod.route('/CEDOntime/', methods=['GET','POST'])
@login_required    
def CEDOntime():
    if 'updatebook' in request.args:
        #print (request.args)
        save_ontime(request.args)
    headers = ontime_headers
    data = CE_ontime_status()
    alias = session['alias']
    return render_template('ce_ontime.html', **locals())