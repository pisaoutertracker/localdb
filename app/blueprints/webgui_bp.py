from flask import Blueprint, render_template
# send_from_directory is used to send files from a directory
from flask import send_from_directory, current_app
import os

bp = Blueprint('main', __name__)


@bp.route('/')
def homeGUI():
    # Serve the static index.html so the home page can be a static file
    return send_from_directory(current_app.static_folder, 'index.html')


@bp.route('/attachments/<filename>')
def getAttachment(filename):
    return send_from_directory("/attachments", filename)


@bp.route('/session_testing_flow')
def session_testing_flow():
    # Serve the session testing flow HTML page from the static/analysis folder
    analysis_dir = os.path.join(current_app.static_folder, 'analysis')
    return send_from_directory(analysis_dir, 'session_testing_flow.html')


@bp.route('/session_results')
def session_results():
    # Serve the session results HTML page from the static/analysis folder
    analysis_dir = os.path.join(current_app.static_folder, 'analysis')
    return send_from_directory(analysis_dir, 'session_results.html')
