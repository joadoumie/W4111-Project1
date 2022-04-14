
"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import json
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash


#JSON RECIPEUID STUFF
with open('ids.json') as f:
  ids_data = json.load(f)

recipe_uid = ids_data["recipeuid"]
ingredient_uid = ids_data["ingredientid"]
review_id = ids_data["reviewid"]
print(ids_data["recipeuid"])
with open('ids.json', 'w') as json_file:
  json.dump(ids_data, json_file)


def increment_recipeID():
  global recipe_uid, ids_data
  recipe_uid += 1
  ids_data["recipeuid"] += 1
  with open('ids.json', 'w') as json_file:
    json.dump(ids_data, json_file)

def increment_ingredientID():
  global ingredient_uid, ids_data
  ingredient_uid += 1
  ids_data["ingredientid"] += 1
  with open('ids.json', 'w') as json_file:
    json.dump(ids_data, json_file)

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

def insert_into_table(table_name, list_of_vals):
  values = "("
  for val in list_of_vals:
    values += str(val)
  values += ")"
  return "INSERT INTO " + table_name + "VALUES " + values

# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "sjc2233"
DB_PASSWORD = "bridge"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print ("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  if not session.get('logged_in'):
    return render_template('login.html')
  return render_template("recipe_home.html")

@app.route('/allrecipes')
def all_recipes():
    """
  request is a special object that Flask provides to access web request information:
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

    # DEBUG: this is debugging code to see what request looks like
    print(request.args)

    #
    # example of a database query
    #
    cursor1 = g.conn.execute("SELECT * FROM recipes")
    recipeIDList = []
    recipeNamesDict = {}
    recipeInstDict = {}
    for result in cursor1:
        recipeIDList.append(result['recipeid'])  # can also be accessed using result[0]
        currRecipeID = result['recipeid']
        recipeNamesDict[currRecipeID]= str(result['recipename']).strip()
        recipeInstDict[currRecipeID]= str(result['instructions']).strip()
    cursor1.close()

    recipeIngredDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from recipes natural join contains_ingredients natural join ingredients
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor = g.conn.execute(temp_sql)
        currRecipeIngred = []
        for result in tempCursor:
            tempAmt = str(result['amount']).strip()
            tempUnit = str(result['unit']).strip()
            tempName = str(result['name']).strip()
            tempStr = tempAmt + ' ' + tempUnit + ' ' + tempName
            currRecipeIngred.append(tempStr)
        recipeIngredDict[curr_recipeID] = currRecipeIngred
        tempCursor.close()

    recipeRatingDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from review natural join users
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor1 = g.conn.execute(temp_sql)
        currReviewList = []
        for result in tempCursor1:
            tempReview = {'reviewid': result['reviewid'],
                          'stars': result['stars'],
                          'content': str(result['content']).strip(),
                          'username': result['username']}
            # tempReview = [result['reviewid'], result['stars'], str(result['content']).strip()]
            currReviewList.append(tempReview)
        recipeRatingDict[curr_recipeID] = currReviewList
        tempCursor1.close()

    print(recipeRatingDict[2][1])

    context1 = dict(recipeIDList=recipeIDList, recipeNamesDict=recipeNamesDict,
                    recipeInstDict=recipeInstDict, recipeIngredDict=recipeIngredDict,
                    recipeRatingDict=recipeRatingDict)
    #
    # render_template looks in the templates/ folder for files.
    # for example, the below file reads template/index.html
    #
    return render_template("allrecipes.html", **context1)

@app.route('/favoriterecipes')
def fave_recipes():
    # DEBUG: this is debugging code to see what request looks like
    print(request.args)

    #
    # example of a database query
    #
    tempfave = """
    select *
    from recipes natural join favorites
    where uid = %d 
    """ % 2 #NEED TO CHANgE THIS
    cursor1 = g.conn.execute(tempfave)
    recipeIDList = []
    recipeNamesDict = {}
    recipeInstDict = {}
    for result in cursor1:
        recipeIDList.append(result['recipeid'])  # can also be accessed using result[0]
        currRecipeID = result['recipeid']
        recipeNamesDict[currRecipeID]= str(result['recipename']).strip()
        recipeInstDict[currRecipeID]= str(result['instructions']).strip()
    cursor1.close()

    recipeIngredDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from recipes natural join contains_ingredients natural join ingredients
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor = g.conn.execute(temp_sql)
        currRecipeIngred = []
        for result in tempCursor:
            tempAmt = str(result['amount']).strip()
            tempUnit = str(result['unit']).strip()
            tempName = str(result['name']).strip()
            tempStr = tempAmt + ' ' + tempUnit + ' ' + tempName
            currRecipeIngred.append(tempStr)
        recipeIngredDict[curr_recipeID] = currRecipeIngred
        tempCursor.close()

    recipeRatingDict = {}
    for curr_recipeID in recipeIDList:
        temp_sql = """
        select *
        from review natural join users
        where recipeID = %d
        """ % (curr_recipeID)
        tempCursor1 = g.conn.execute(temp_sql)
        currReviewList = []
        for result in tempCursor1:
            tempReview = {'reviewid': result['reviewid'],
                          'stars': result['stars'],
                          'content': str(result['content']).strip(),
                          'username': result['username']}
            # tempReview = [result['reviewid'], result['stars'], str(result['content']).strip()]
            currReviewList.append(tempReview)
        recipeRatingDict[curr_recipeID] = currReviewList
        tempCursor1.close()

    context2 = dict(recipeIDList=recipeIDList, recipeNamesDict=recipeNamesDict,
                    recipeInstDict=recipeInstDict, recipeIngredDict=recipeIngredDict,
                    recipeRatingDict=recipeRatingDict)

    return render_template("favoriterecipes.html", **context2)

@app.route('/reviews')
def review_recipes():
    return render_template("reviewrecipe.html")

@app.route('/logout')
def logout():
  session['logged_in'] = False
  return index()

@app.route('/another')
def another():
  return render_template("anotherfile.html")

@app.route('/home')
def recipe_home():
  return render_template("recipe_home.html")

@app.route('/addingredienterror')
def add_ingr_err():
  return render_template("addingingredienterror.html")

@app.route('/testnav')
def navbar():
  return render_template("testnavbar.html")

@app.route('/addfavorite', methods=['POST'])
def follow_add():
    recipeid = request.form['recipeid']
    uid = request.form['uid']
    cmd = 'INSERT INTO favorites VALUES (:name1, :name2)';
    g.conn.execute(text(cmd), name1=recipeid, name2=uid);
    return redirect('/home')

@app.route('/addfavorite', methods=['POST'])
def favorite_add():
    recipeid = request.form['recipeid']
    uid = request.form['uid']
    cmd = 'INSERT INTO favorites VALUES (:name1, :name2)';
    g.conn.execute(text(cmd), name1=recipeid, name2=uid);
    return redirect('/home')

@app.route('/addreview', methods=['POST'])
def review_add():
    recipeid = request.form['recipeid']
    stars = request.form['stars']
    content = request.form['reviewtext']
    uid = request.form['uid']
    # print(recipe_name, instructions, ingredients)
    cmd = 'INSERT INTO review VALUES (:name1, :name2, :name3, :name4, :name5)';
    g.conn.execute(text(cmd), name1=review_id, name2=content,
                   name3=stars, name4=recipeid, name5=uid);
    return redirect('/home')

@app.route('/addrecipe', methods=['POST'])
def recipe_add():
  recipe_name = request.form['recipename']
  instructions = request.form['instructions']
  print (recipe_name, instructions)
  cmd = 'INSERT INTO recipes VALUES (:name1, :name2, :name3)';
  g.conn.execute(text(cmd), name1 = recipe_uid, name2 = recipe_name, name3 = instructions);
  increment_recipeID()
  return redirect('/home')


@app.route('/addingredient', methods=['POST'])
def ingredient_add():
  ingredient_name = request.form['ingredient_name']
  ingredient_qty = request.form['quantity']
  ingredient_unit = request.form['unit']
  print (ingredient_name, ingredient_qty)
  recipe_exists = g.conn.execute('SELECT * FROM recipes WHERE recipeID = ' + str(recipe_uid)).scalar()
  if not recipe_exists:
    return redirect('/addingredienterror')
  ingredient_exists = g.conn.execute('SELECT * FROM ingredients WHERE name = ' + " ' + " + ingredient_name + "'").scalar()
  if not ingredient_exists:
    #Add ingredient to ingredients table.
    local_ingr_id = ingredient_uid
    cmd = 'INSERT INTO ingredients VALUES (:name1, :name2)';
    g.conn.execute(text(cmd), name1=local_ingr_id, name2=ingredient_name);
  else:
    local_ingr_id = ingredient_exists['ingredientID']

  cmd = 'INSERT INTO contains_ingredients VALUES (:name1, :name2, :name3, :name4)';
  g.conn.execute(text(cmd), name1=local_ingr_id, name2=recipe_uid, name3=ingredient_qty, name4=ingredient_unit);
  increment_ingredientID()
  return redirect('/home')


@app.route('/existing_login')
def existing_login():
  return render_template('existinglogin.html')

@app.route('/create_new_login')
def create_new_login():
  return render_template('createnewaccount.html')

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login_attempt', methods =['POST'])
def do_login():
  print("Testing testing")
  if request.form['password'] == 'password' and request.form['username'] == 'admin':
    session['logged_in'] = True
    return index()
  else:
    print("flash that password")
    flash('wrong password!')
  return index()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print ("running on %s:%d" % (HOST, PORT))
    app.secret_key = os.urandom(12)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
