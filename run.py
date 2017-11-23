#!flask/bin/python
from application import app
app.run(
    host="0.0.0.0",
    # host="localhost",
    # host="192.168.0.18",
    port=int("8500"),
    # port=int("8080"),
    debug=True
)