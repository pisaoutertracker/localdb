from flask import Blueprint, render_template
# send_from_directory is used to send files from a directory
from flask import send_from_directory, current_app

bp = Blueprint('main', __name__)


@bp.route('/')
def homeGUI():
    # Serve the static index.html so the home page can be a static file
    return send_from_directory(current_app.static_folder, 'index.html')


@bp.route('/attachments/<filename>')
def getAttachment(filename):
    return send_from_directory("/attachments", filename)
