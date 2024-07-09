from flask import Blueprint, render_template
#send_from_directory is used to send files from a directory
from flask import send_from_directory

bp = Blueprint('main', __name__)

@bp.route('/')
def homeGUI():
    return render_template('home.html')

@bp.route('/connect_cables.html')
def connectGUI():
    return render_template('connect_cables.html')

@bp.route('/disconnect_cables.html')
def disconnectGUI():
    return render_template('disconnect_cables.html')

@bp.route('/logbook.html')
def logbookGUI():
    return render_template('logbook.html')

#add route to fetch attachments from /attachments folder

@bp.route('/attachments/<filename>')
def getAttachment(filename):
    return send_from_directory("/attachments", filename)