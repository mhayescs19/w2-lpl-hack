import os

from flask import Flask, request, redirect, flash, url_for, render_template, jsonify
from werkzeug.utils import secure_filename

import textract

app = Flask(__name__)

UPLOAD_FOLDER = 'static/user/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def hello_world():  # put application's code here
    return render_template('home.html')


@app.route("/upload", methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url, code=404)
        file = request.files['file']
        if file.filename == '':
            flash("no selected file")
            return redirect(request.url, code=404)
        if file and (
                file.filename.rsplit('.', 1)[1].lower() == "pdf" or file.filename.rsplit('.', 1)[1].lower() == "jpeg" or file.filename.rsplit('.', 1)[1].lower() == 'jpg' ):
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            map = textract.init_text_search(os.path.join(UPLOAD_FOLDER, filename))
            return jsonify(map)
    return '''
        <!doctype html>
        <title>Upload new File</title>
        <h1>Upload new File</h1>
        <form method=post enctype=multipart/form-data>
          <input type=file name=file>
          <input type=submit value=Upload>
        </form>
    '''


if __name__ == '__main__':
    app.run()
