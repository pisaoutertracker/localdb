from flask import Blueprint, render_template
#send_from_directory is used to send files from a directory
from flask import send_from_directory

bp = Blueprint('main', __name__)

@bp.route('/')
def homeGUI():
    return render_template('home.html')

@bp.route('/attachments/<filename>')
def getAttachment(filename):
    return send_from_directory("/attachments", filename)
