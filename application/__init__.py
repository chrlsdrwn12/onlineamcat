from flask import Flask

app = Flask(__name__)
from application import views

from application import router
app.add_url_rule('/test', 'test', router.test)
#app.add_url_rule('/CEDOntime', 'CEDOntime', router.CEDOntime)

from application.router import CEmod # /CE/status
app.register_blueprint(CEmod)